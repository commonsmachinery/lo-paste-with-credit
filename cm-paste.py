#! /usr/bin/python3
#
# vocab - definitions and human-readable names for metadata terms
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Artem Popov <artfwo@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

import libcredit
from xml.dom import minidom

import uno
import unohelper

from com.sun.star.awt import Size
from com.sun.star.task import XJobExecutor
from com.sun.star.beans import PropertyValue
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
from com.sun.star.text.TextContentAnchorType import AS_CHARACTER
from com.sun.star.text.TextContentAnchorType import AT_PARAGRAPH

class LOCreditFormatter(libcredit.CreditFormatter):
    """
    Credit writer that adds text to LibreOffice writer document using UNO. 
    """
    def __init__(self, text, cursor):
        self.text = text
        self.cursor = cursor
        self.cursor.collapseToEnd()

    def begin(self):
        pass

    def end(self):
        pass

    def begin_sources(self, label=None):
        self.add_text(" " + label)
        self.text.insertControlCharacter(self.cursor, PARAGRAPH_BREAK, 0)

    def end_sources(self):
        pass

    def begin_source(self):
        pass

    def end_source(self):
        self.text.insertControlCharacter(self.cursor, PARAGRAPH_BREAK, 0)

    def add_title(self, text, url=None):
        self.add_url(text, url)

    def add_attrib(self, text, url=None):
        self.add_url(text, url)

    def add_license(self, text, url=None):
        self.add_url(text, url)

    def add_text(self, text):
        self.text.insertString(self.cursor, text, False)

    def add_url(self, text, url=None):
        if url:
            length = len(text)
            self.text.insertString(self.cursor, text, False)
            self.cursor.goLeft (length, False)
            self.cursor.goRight (length, True)
            self.cursor.setPropertyValue ("HyperLinkURL", url)
            self.cursor.goRight (length, False)
        else:
            self.add_text(text)

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

            img_clip = next(d for d in data_flavors if d.MimeType == "image/png")
            img_byteseq = clip.getContents().getTransferData(img_clip)

            credit = libcredit.Credit(rdf)

            # access the current writer document
            desktop = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self.ctx)

            model = desktop.getCurrentComponent()
            controller = model.getCurrentController()
            text = model.Text

            """
            # paste image - hack, the api should be used here instead of .uno
            dispatch_helper = self.ctx.ServiceManager.createInstance(
                "com.sun.star.frame.DispatchHelper"); 
            dispatch_helper.executeDispatch(controller, ".uno:Paste", "", 0, tuple())
            dispatch_helper.executeDispatch(controller, ".uno:Escape", "", 0, tuple())

            # find the newly pasted image (last in line)
            graphics_access = model.getGraphicObjects()
            last_name = graphics_access.getElementNames()[-1]
            last_obj = graphics_access.getByName(last_name)
            """

            # create the caption in the paragraph after image
            #cursor = text.createTextCursorByRange(last_obj.getAnchor())
            #cursor.gotoNextParagraph(False)
            view_cursor = controller.getViewCursor()
            cursor = view_cursor.getText().createTextCursorByRange(view_cursor)
            cursor.gotoStartOfSentence(False)
            cursor.gotoEndOfSentence(True)

            #credit_writer = LOCreditFormatter(text, cursor)
            #credit.format(credit_writer)

            text_frame = model.createInstance("com.sun.star.text.TextFrame")
            text_frame.setSize( Size(15000,400))
            text_frame.setPropertyValue("AnchorType", AT_PARAGRAPH)

            text.insertTextContent(cursor, text_frame, 0)
            frame_text = text_frame.getText()

            # create the image directly from clipboard data instead of .uno:Paste
            img_stream = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.io.SequenceInputStream", self.ctx)
            img_stream.initialize((img_byteseq,))
            graphic_provider = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.graphic.GraphicProvider", self.ctx)

            stream_property = PropertyValue()
            stream_property.Name = "InputStream"
            stream_property.Value = img_stream

            graphic_descriptor = graphic_provider.queryGraphicDescriptor((stream_property,))
            graphic = graphic_provider.queryGraphic((stream_property,))
            size = graphic_descriptor.getPropertyValue("SizePixel")

            image = model.createInstance('com.sun.star.text.TextGraphicObject')
            image.setPropertyValue("Graphic", graphic)
            # a hack to enlarge the tiny pasted images
            image.setPropertyValue("Width", size.Width * 20)
            image.setPropertyValue("Height", size.Height * 20)

            cursor = frame_text.createTextCursor() # FIXME: should use the real cursor here
            frame_text.insertTextContent(cursor, image, False)
            cursor.gotoNextParagraph(False)

            credit_writer = LOCreditFormatter(frame_text, cursor)
            credit.format(credit_writer)

            image.setPropertyValue("RelativeWidth", 100)
            #image.setPropertyValue("RelativeHeight", 100)
            image.setPropertyValue("IsSyncHeightToWidth", True)

            # set image description
            credit_writer = libcredit.TextCreditFormatter()
            credit.format(credit_writer, source_depth=0)
            image.setPropertyValue("Title", credit_writer.get_text())

            credit_writer = libcredit.TextCreditFormatter()
            credit.format(credit_writer)
            image.setPropertyValue("Description", credit_writer.get_text())
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
