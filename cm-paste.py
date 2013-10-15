#! /usr/bin/python3
#
# vocab - definitions and human-readable names for metadata terms
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Artem Popov <artfwo@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

from RDFMetadata import parser
from RDFMetadata import vocab
from xml.dom import minidom

import uno
import unohelper

from com.sun.star.task import XJobExecutor

license_labels = {
    "http://creativecommons.org/licenses/by/3.0/": "CC BY 3.0",
    "http://creativecommons.org/licenses/by-nc/3.0/": "CC BY-NC 3.0",
    "http://creativecommons.org/licenses/by-nc-nd/3.0/": "CC BY-NC-ND 3.0",
    "http://creativecommons.org/licenses/by-nc-sa/3.0/": "CC BY-NC-SA 3.0",
    "http://creativecommons.org/licenses/by-nd/3.0/": "CC BY-ND 3.0",
    "http://creativecommons.org/licenses/by-sa/3.0/": "CC BY-SA 3.0",
}

class PasteJob(unohelper.Base, XJobExecutor):
    def __init__(self, ctx):
        self.ctx = ctx

    def trigger(self, args):
        clip = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.datatransfer.clipboard.SystemClipboard", self.ctx)

        contents = clip.getContents()
        data_flavors = contents.getTransferDataFlavors()
        mimeTypes = [d.MimeType for d in data_flavors]

        if "image/png" in mimeTypes and "application/rdf+xml" in mimeTypes:
            # if both image and RDF reside in clipboard, it's likely our cause
            rdf_clip = next(d for d in data_flavors if d.MimeType == "application/rdf+xml")
            rdf = clip.getContents().getTransferData(rdf_clip).value.decode('utf-16')

            doc = minidom.parseString(rdf)
            rdfs = doc.getElementsByTagNameNS("http://www.w3.org/1999/02/22-rdf-syntax-ns#", 'RDF')
            root = next(parser.parse_RDFXML(doc=doc, root_element=r) for r in rdfs)

            # access the current writer document
            desktop = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self.ctx)

            model = desktop.getCurrentComponent()
            controller = model.getCurrentController()
            text = model.Text

            # paste image - hack, the api should be used here instead of .uno
            dispatch_helper = self.ctx.ServiceManager.createInstance(
                "com.sun.star.frame.DispatchHelper"); 
            dispatch_helper.executeDispatch(controller, ".uno:Paste", "", 0, tuple())
            dispatch_helper.executeDispatch(controller, ".uno:Escape", "", 0, tuple())

            # find the newly pasted image (last in line)
            graphics_access = model.getGraphicObjects()
            last_name = graphics_access.getElementNames()[-1]
            last_obj = graphics_access.getByName(last_name)

            # create the caption in the paragraph after image
            cursor = text.createTextCursorByRange(last_obj.getAnchor())
            cursor.gotoNextParagraph(False)

            credit = self.get_credit_string(root)
            text.insertString(cursor, credit, 0)
        else:
            # access the current writer document
            desktop = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self.ctx)

            model = desktop.getCurrentComponent()
            controller = model.getCurrentController()
            # just paste whatever is in clipboard
            dispatch_helper = self.ctx.ServiceManager.createInstance(
                "com.sun.star.frame.DispatchHelper"); 
            dispatch_helper.executeDispatch(controller, ".uno:Paste", "", 0, tuple())            


    def get_credit_string(self, root):
        # working with default resource for now
        default_res = root.resource_nodes['']

        title = self.get_any_resource(default_res, [
            vocab.dc.title,
        ])
        if title is not None:
            title = title.value
        else:
            title = "Image"

        author = self.get_any_resource(default_res, [
            vocab.dc.creator,
            vocab.cc.attributionName,
        ])
        if author is not None:
            author = " by " + author.value
        else:
            author = ""
        
        license = self.get_any_resource(default_res, [
            vocab.xhtml.license,
            vocab.dcterms.license,
            vocab.cc.license,
        ])
        if license is not None:
            if license.uri in license_labels:
                license = " Licensed under " + license_labels[license.uri]
            else:
                license = " Licensed under " + license.uri
        else:
            license = ""

        credit = title + author + "." + license
        return credit

    def get_any_resource(self, resource, terms):
        for t in terms:
            for p in resource.predicates:
                if p.uri == t.qname:
                    return p.object


g_ImplementationHelper = unohelper.ImplementationHelper()

g_ImplementationHelper.addImplementation(
    PasteJob,
    "se.commonsmachinery.extensions.paste_with_credit.PasteJob", # as defined in the .xcu
    ("com.sun.star.task.Job",)
)


if __name__ == "__main__":
    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", localContext)

    # connect to the running office, start as:
    #     soffice "--accept=socket,host=localhost,port=2002;urp;" --writer
    ctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    smgr = ctx.ServiceManager

    job = PasteJob(ctx)
    job.trigger(None)

    # Python-UNO bridge workaround: call a synchronous method, before the python
    # process exits to sync the remote-bridge cache, otherwise an async call
    # may not terminate properly.
    ctx.ServiceManager
