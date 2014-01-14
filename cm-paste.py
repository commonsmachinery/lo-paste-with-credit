#! /usr/bin/python3
#
# lo-paste-with-credit - LibreOffice extensions for pasting images with metadata
#
# Copyright 2013-2014 Commons Machinery http://commonsmachinery.se/
#
# Authors: Artem Popov <artfwo@commonsmachinery.se>
#          Peter Liljenberg <peter@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

import libcredit
from xml.dom import minidom

import uno
import unohelper

from com.sun.star.awt import Size
from com.sun.star.awt import Point
from com.sun.star.task import XJobExecutor
from com.sun.star.beans import PropertyValue
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
from com.sun.star.text.TextContentAnchorType import AS_CHARACTER
from com.sun.star.text.TextContentAnchorType import AT_PARAGRAPH
from com.sun.star.container import NoSuchElementException

BOOKMARK_BASE_NAME = "$image-with-metadata$"

class LOCreditFormatter(libcredit.CreditFormatter):
    """
    Credit writer that adds text to LibreOffice writer document using UNO.
    """
    def __init__(self, text, cursor, hyperlinks=True, metadata = None):
        self.text = text
        self.cursor = cursor
        self.cursor.collapseToEnd()
        self.hyperlinks = hyperlinks

        self.metadata = metadata

        self.subject_stack = []
        self.current_subject = None

    def begin(self, subject_uri=None):
        if self.metadata:
            if subject_uri is not None:
                new_subject = self.metadata.uri(subject_uri)
            else:
                new_subject = None
                
            if self.current_subject is not None and new_subject is not None:
                # Generate a dc:source statement from the previous level
                self.metadata.add_statement(
                    self.current_subject,
                    self.metadata.uri('http://purl.org/dc/elements/1.1/source'),
                    new_subject)

            self.subject_stack.append(self.current_subject)
            self.current_subject = new_subject

    def end(self):
        if self.metadata:
            self.current_subject = self.subject_stack.pop()

    def begin_sources(self, label=None):
        self.add_text(" " + label)
        self.text.insertControlCharacter(self.cursor, PARAGRAPH_BREAK, 0)

    def end_sources(self):
        pass

    def begin_source(self):
        pass

    def end_source(self):
        self.text.insertControlCharacter(self.cursor, PARAGRAPH_BREAK, 0)

    def add_title(self, token):
        self.add_token(token)

    def add_attrib(self, token):
        self.add_token(token)

    def add_license(self, token):
        self.add_token(token)

    def add_text(self, text):
        self.text.insertString(self.cursor, text, False)

    def add_token(self, token):
        length = len(token.text)
        self.text.insertString(self.cursor, token.text, False)
        self.cursor.goLeft(length, False)
        self.cursor.goRight(length, True)

        if token.url and self.hyperlinks:
            self.cursor.setPropertyValue("HyperLinkURL", token.url)

        if self.current_subject and token.text_property:
            # Turn the text into a metadata field that's the object of
            # an RDFa statement
            md = self.metadata.create_meta_element()
            self.text.insertTextContent(self.cursor, md, True)
            self.metadata.add_rdfa_statements(
                self.current_subject,
                (self.metadata.uri(token.text_property), ),
                md)

        self.cursor.goRight(length, False)

        if self.current_subject and token.url_property:
            # Add regular statement for the URL predicate
            self.metadata.add_statement(
                self.current_subject,
                self.metadata.uri(token.url_property),
                self.metadata.uri(token.url))


class Metadata(object):
    """Helper functions for working with the RDF metadata APIs"""

    GRAPH_FILE = 'metadata/sources.rdf'
    GRAPH_TYPE_URI = 'http://purl.org/dc/terms/ProvenanceStatement'
    
    def __init__(self, ctx, model):
        self.ctx = ctx
        self.model = model
        self.repository = self.model.getRDFRepository()

        # Load or create graph
        type_uri = self.uri(self.GRAPH_TYPE_URI)
        graph_uris = self.model.getMetadataGraphsWithType(type_uri)
        if graph_uris:
            graph_uri = graph_uris[0]
        else:
            graph_uri = self.model.addMetadataFile(self.GRAPH_FILE, (type_uri, ))

        self.graph = self.repository.getGraph(graph_uri)


    def uri(self, uri):
        return self.ctx.ServiceManager.createInstanceWithArguments(
            "com.sun.star.rdf.URI", (uri, ))

    def literal(self, value):
        return self.ctx.ServiceManager.createInstanceWithArguments(
            "com.sun.star.rdf.Literal", (value, ))
    
    def add_statement(self, subject, predicate, obj):
        self.graph.addStatement(subject, predicate, obj)

    def add_rdfa_statements(self, subject, predicates, literal):
        self.repository.setStatementRDFa(subject, predicates, literal, '', None)

    def create_meta_element(self):
        return self.model.createInstance('com.sun.star.text.InContentMetadata')        

    def dump_graph(self):
        statements = self.repository.getStatements(None, None, None)
        while statements.hasMoreElements():
            s = statements.nextElement()
            self.dump_statement(s)

    def dump_statement(self, s):
        if hasattr(s.Object, 'Value'):
            obj = '"{0}"'.format(s.Object.Value)
        else:
            obj = '<{0}>'.format(s.Object.StringValue)

        if s.Graph:
            g = s.Graph.StringValue
        else:
            g = 'RDFa'

        print('<{0}> <{1}> {2} . # {3}'.format(
                s.Subject.StringValue,
                s.Predicate.StringValue,
                obj, g))


class PasteWithCreditJob(unohelper.Base, XJobExecutor):
    def __init__(self, ctx):
        self.ctx = ctx

    def trigger(self, args):
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)

        model = desktop.getCurrentComponent()
        controller = model.getCurrentController()

        image_with_metadata = self._get_image_with_metadata()
        if not image_with_metadata:
            # just paste whatever is in clipboard
            dispatch_helper = self.ctx.ServiceManager.createInstance(
                "com.sun.star.frame.DispatchHelper");
            dispatch_helper.executeDispatch(controller, ".uno:Paste", "", 0, tuple())
            return

        rdf, descriptor, graphic = image_with_metadata
        img_size = descriptor.getPropertyValue("SizePixel")

        if model.supportsService("com.sun.star.text.TextDocument"):
            # Metadata is only supported in text documents
            metadata = Metadata(ctx, model)

            # create a frame to hold the image with caption
            text_frame = model.createInstance("com.sun.star.text.TextFrame")
            text_frame.setSize(Size(15000,400))
            text_frame.setPropertyValue("AnchorType", AT_PARAGRAPH)

            # duplicate current cursor
            view_cursor = controller.getViewCursor()
            cursor = view_cursor.getText().createTextCursorByRange(view_cursor)
            cursor.gotoStartOfSentence(False)
            cursor.gotoEndOfSentence(True)

            # insert text frame
            text = model.Text
            text.insertTextContent(cursor, text_frame, 0)
            frame_text = text_frame.getText()

            cursor = frame_text.createTextCursor()

            # Add a <text:bookmark> tag to serve as anchor for the RDF
            # and give us a subject URI.  Ideally, we would get this
            # from the image but that isn't possible with current
            # APIs.

            bookmark = model.createInstance("com.sun.star.text.Bookmark")
            bookmark.setName(BOOKMARK_BASE_NAME)
            frame_text.insertTextContent(cursor, bookmark, False)
            bookmark.ensureMetadataReference()
            cursor.gotoEnd(False)

            # create a TextGraphicObject to hold the image
            image = model.createInstance("com.sun.star.text.TextGraphicObject")
            image.setPropertyValue("Graphic", graphic)
            # hack to enlarge the tiny pasted images
            image.setPropertyValue("Width", img_size.Width * 20)
            image.setPropertyValue("Height", img_size.Height * 20)
            
            frame_text.insertTextContent(cursor, image, False)
            
            # add the credit as text below the image
            credit = libcredit.Credit(rdf)
            credit_writer = LOCreditFormatter(frame_text, cursor, metadata = metadata)
            credit.format(credit_writer, subject_uri = bookmark.StringValue)

            # scale the image to fit the frame
            image.setPropertyValue("RelativeWidth", 100)
            #image.setPropertyValue("RelativeHeight", 100)
            image.setPropertyValue("IsSyncHeightToWidth", True)

            # set image title (no sources)
            credit_writer = libcredit.TextCreditFormatter()
            credit.format(credit_writer, source_depth=0)
            image.setPropertyValue("Title", credit_writer.get_text())

            # set image title (credit with sources)
            credit_writer = libcredit.TextCreditFormatter()
            credit.format(credit_writer)
            image.setPropertyValue("Description", credit_writer.get_text())

            # DEBUG:
            # metadata.dump_graph()

        elif model.supportsService("com.sun.star.presentation.PresentationDocument"):
            page = controller.getCurrentPage()

            # begin pasting
            shape = model.createInstance("com.sun.star.drawing.GraphicObjectShape")
            shape.Graphic = graphic
            shape.setSize(Size(img_size.Width * 20, img_size.Height * 20))

            page.add(shape)

            attr = uno.createUnoStruct("com.sun.star.xml.AttributeData")
            attr.Value = rdf
            attributes = shape.UserDefinedAttributes
            attributes.insertByName("cm-metadata", attr)
            shape.UserDefinedAttributes = attributes

            size = shape.Size
            shape.setPosition(Point(
                int((page.Width - size.Width) / 2),
                int((page.Height - size.Height) / 2))
            )

    # returns a tuple consisting of (str, GraphicDescriptor, Graphic) or None
    def _get_image_with_metadata(self):
        clip = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.datatransfer.clipboard.SystemClipboard", self.ctx)

        contents = clip.getContents()
        data_flavors = contents.getTransferDataFlavors()
        mimeTypes = [d.MimeType for d in data_flavors]

        if "image/png" in mimeTypes and "application/rdf+xml" in mimeTypes:
            rdf_clip = next(d for d in data_flavors if d.MimeType == "application/rdf+xml")
            rdf = clip.getContents().getTransferData(rdf_clip).value.decode("utf-16")

            img_clip = next(d for d in data_flavors if d.MimeType == "image/png")
            img = clip.getContents().getTransferData(img_clip)

            img_stream = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.io.SequenceInputStream", self.ctx)
            img_stream.initialize((img,))
            graphic_provider = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.graphic.GraphicProvider", self.ctx)

            stream_property = PropertyValue()
            stream_property.Name = "InputStream"
            stream_property.Value = img_stream

            descriptor = graphic_provider.queryGraphicDescriptor((stream_property,))
            graphic = graphic_provider.queryGraphic((stream_property,))
            #size = descriptor.getPropertyValue("SizePixel")
            return (rdf, descriptor, graphic)

        return None

class InsertCreditsJob(unohelper.Base, XJobExecutor):
    def __init__(self, ctx):
        self.ctx = ctx

    def trigger(self, args):
        # access the current writer document
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)

        model = desktop.getCurrentComponent()
        controller = model.getCurrentController()
        presentation = model.Presentation

        pages = model.getDrawPages()
        credits = []
        for page_num in range(pages.getCount()):
            page = pages.getByIndex(page_num)
            for shape_num in range(page.getCount()):
                shape = page.getByIndex(shape_num)
                try:
                    rdf = shape.UserDefinedAttributes.getByName("cm-metadata").Value
                    credit = libcredit.Credit(rdf)
                    credits.append(credit)
                except NoSuchElementException:
                    pass

        # create a TextShape with credits on the current page
        page = controller.getCurrentPage()
        shape = model.createInstance("com.sun.star.drawing.TextShape")
        shape.TextAutoGrowHeight = True
        shape.TextAutoGrowWidth = True

        page.add(shape)

        text = shape.Text
        cursor = text.createTextCursor()
        text.insertString(cursor, "This presentation includes the following works:", 0)
        text.insertControlCharacter(cursor, PARAGRAPH_BREAK, 0)
        text.insertControlCharacter(cursor, PARAGRAPH_BREAK, 0)
        cursor.gotoEnd(False)

        for credit in credits:
            # in Impress cursor seems to support com.sun.star.style.CharacterProperties
            # but trying to set HyperLinkURL property raises an UnknownPropertyException
            # so let's just disable hyperlinks for now
            tf = LOCreditFormatter(text, cursor, hyperlinks=False)
            credit.format(tf, source_depth=0)
            text.insertControlCharacter(cursor, PARAGRAPH_BREAK, 0)

        size = shape.Size
        shape.setPosition(Point(
            int((page.Width - size.Width) / 2),
            int((page.Height - size.Height) / 2))
        )

g_ImplementationHelper = unohelper.ImplementationHelper()

# job class as defined in the .xcu
g_ImplementationHelper.addImplementation(
    PasteWithCreditJob,
    "se.commonsmachinery.extensions.paste_with_credit.PasteWithCreditJob",
    ("com.sun.star.task.Job",)
)

# job class as defined in the .xcu
g_ImplementationHelper.addImplementation(
    InsertCreditsJob,
    "se.commonsmachinery.extensions.paste_with_credit.InsertCreditsJob",
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

    job = PasteWithCreditJob(ctx)
    job.trigger(None)

    # Python-UNO bridge workaround: call a synchronous method, before the python
    # process exits to sync the remote-bridge cache, otherwise an async call
    # may not terminate properly.
    ctx.ServiceManager
