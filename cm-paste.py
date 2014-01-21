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
import tempfile, os
import uuid

import uno
import unohelper

from com.sun.star.awt import Size
from com.sun.star.awt import Point
from com.sun.star.task import XJob
from com.sun.star.task import XJobExecutor
from com.sun.star.beans import PropertyValue
from com.sun.star.io import XOutputStream

from com.sun.star.datatransfer import DataFlavor
from com.sun.star.datatransfer import XTransferable
from com.sun.star.datatransfer.clipboard import XClipboardOwner

from com.sun.star.lang import XInitialization
from com.sun.star.frame import XDispatch
from com.sun.star.frame import XDispatchProvider
from com.sun.star.ui import XContextMenuInterceptor
from com.sun.star.ui.ContextMenuInterceptorAction import IGNORED
from com.sun.star.ui.ContextMenuInterceptorAction import EXECUTE_MODIFIED

from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
from com.sun.star.text.TextContentAnchorType import AS_CHARACTER
from com.sun.star.text.TextContentAnchorType import AT_PARAGRAPH
from com.sun.star.rdf.FileFormat import RDF_XML
from com.sun.star.ui.ActionTriggerSeparatorType import LINE

from com.sun.star.container import NoSuchElementException


BOOKMARK_BASE_NAME = "$metadata-tag-do-not-edit$"


class StringOutputStream(unohelper.Base, XOutputStream):
    def __init__(self):
        self.s = uno.ByteSequence('')

    def writeBytes(self, data):
        self.s = self.s + data

    def flush(self):
        pass

    def closeOutput(self):
        pass

    def __str__(self):
        return self.s.value.decode('utf-8')

def copy_statements(repository, subject, seen_subjects, graph):
    if subject.StringValue in seen_subjects:
        return

    seen_subjects[subject.StringValue] = 1

    statements = repository.getStatements(subject, None, None)
    while statements.hasMoreElements():
        s = statements.nextElement()

        # Only copy if not a duplicate
        if not graph.getStatements(s.Subject, s.Predicate, s.Object).hasMoreElements():
            graph.addStatement(s.Subject, s.Predicate, s.Object)

            if not hasattr(s.Object, 'Value'):
                # Recurse over non-literal
                copy_statements(repository, s.Object, seen_subjects, graph)

def uri(ctx, string):
    return ctx.ServiceManager.createInstanceWithArguments(
        "com.sun.star.rdf.URI", (string, ))

def get_image_metadata(ctx, model, name):

    bookmark = model.getBookmarks().getByName(name)

    repository = model.getRDFRepository()

    ss = StringOutputStream()

    seen_subjects = {}

    # Copy statements to a temporary graph
    graph_uri = uri(ctx, 'urn:' + str(uuid.uuid4()) + '#temp')
    target_graph = repository.createGraph(graph_uri)
    try:
        copy_statements(repository, bookmark, seen_subjects, target_graph)

        # Add the <> dc:source <imageURI> triple that libcredit uses to find the metadata
        target_graph.addStatement(model, uri(ctx, 'http://purl.org/dc/elements/1.1/source'), bookmark)

        repository.exportGraph(RDF_XML, ss, graph_uri, model)
    finally:
        repository.destroyGraph(graph_uri)

    return str(ss)


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
            frame_text.insertTextContent(cursor, bookmark, False)
            bookmark.ensureMetadataReference()
            bookmark.setName(BOOKMARK_BASE_NAME + bookmark.LocalName)
            cursor.gotoEnd(False)

            # create a TextGraphicObject to hold the image
            image = model.createInstance("com.sun.star.text.TextGraphicObject")
            image.setPropertyValue("Graphic", graphic)
            # hack to enlarge the tiny pasted images
            image.setPropertyValue("Width", img_size.Width * 20)
            image.setPropertyValue("Height", img_size.Height * 20)
            image.setName(bookmark.getName())

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
            rdf = clip.getContents().getTransferData(rdf_clip).value

            # We might get both UTF-8 and UTF-16 here.
            try:
                rdf = rdf.decode('utf-8')
            except UnicodeError:
                rdf = rdf.decode('utf-16')

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


class ImageWithMetadataTransferable(unohelper.Base, XTransferable):
    def __init__(self, img_data, rdf_data):
        self._rdf_type = "application/rdf+xml"
        self._img_type = "image/png"

        self._img_data = img_data
        self._rdf_data = rdf_data.encode("utf-8")

    def getTransferData(self, flavor):
        if flavor.MimeType == self._rdf_type:
            return uno.ByteSequence(self._rdf_data)
        if flavor.MimeType == self._img_type:
            return uno.ByteSequence(self._img_data)

    def getTransferDataFlavors(self):
        df_rdf = DataFlavor()
        df_rdf.MimeType = self._rdf_type
        df_rdf.HumanPresentableName = ""
        #df_rdf.DataType = uno.getTypeByName("[]byte")
        df_rdf.DataType = uno.getTypeByName("string")

        df_img = DataFlavor()
        df_img.MimeType = self._img_type
        df_img.HumanPresentableName = ""
        df_img.DataType = uno.getTypeByName("[]byte")

        return (df_rdf, df_img)

    def isDataFlavorSupported(self, flavor):
        return flavor.MimeType == self._rdf_type or \
               flavor.MimeType == self._img_type


class ImageWithMetadataClipboardOwner(unohelper.Base, XClipboardOwner):
    def __init__(self):
        self.is_owner = True

    def lostOwnership(self, clipboard, transferable):
        self.is_owner = False


class CopyWithMetadataJob(unohelper.Base, XJobExecutor):
    def __init__(self, ctx):
        self.ctx = ctx
        self.clip_owner = None

    def trigger(self, args):
        # access the current writer document
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)

        model = desktop.getCurrentComponent()
        controller = model.getCurrentController()
        selection = controller.getSelection()

        if selection.supportsService("com.sun.star.text.TextGraphicObject") and selection.getName():
            img_name = selection.getName()

            # use tempfile to export graphic
            temp = tempfile.NamedTemporaryFile(delete=False)

            url_property = PropertyValue()
            url_property.Name = "URL"
            url_property.Value = "file:///" + temp.name

            # sadly, OutputStream doesn't work
            #stream_property = PropertyValue()
            #stream_property.Name = "OutputStream"
            #stream_property.Value = out_stream

            mime_property = PropertyValue()
            mime_property.Name = "MimeType"
            mime_property.Value = "image/png"

            graphic_provider = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.graphic.GraphicProvider", self.ctx)
            graphic_provider.storeGraphic(selection.Graphic, (url_property, mime_property))

            temp.close()
            img_data = open(temp.name, "rb").read()
            os.unlink(temp.name)

            img_metadata = get_image_metadata(self.ctx, model, img_name)

            img_transferable = ImageWithMetadataTransferable(img_data, img_metadata)
            self.clip_owner = ImageWithMetadataClipboardOwner()
            clip = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.datatransfer.clipboard.SystemClipboard", self.ctx)
            clip.setContents(img_transferable, self.clip_owner)


class ContextInterceptor(unohelper.Base, XContextMenuInterceptor):
    def __init__ (self, ctx):
        self.ctx = ctx

    def notifyContextMenuExecute (self, event):
        menu = event.ActionTriggerContainer
        selection = event.Selection.getSelection()

        if selection.supportsService("com.sun.star.text.TextGraphicObject"):
            # TextGraphicObject implicitly supports XNamed
            # (not shown in the supported service names)
            img_name = selection.getName()

            if img_name.startswith("$metadata-tag-do-not-edit$"):
                num_items = menu.Count

                separator = menu.createInstance("com.sun.star.ui.ActionTriggerSeparator")
                separator.SeparatorType = LINE

                menu.insertByIndex(num_items + 0, separator)

                menu_item = menu.createInstance("com.sun.star.ui.ActionTrigger")
                menu_item.setPropertyValue("Text", "Copy with metadata")
                menu_item.setPropertyValue("CommandURL", u"se.commonsmachinery.extensions.paste_with_credit.Menu:CopyWithMetadata")
                menu.insertByIndex(num_items + 1, menu_item)

            return EXECUTE_MODIFIED
        # otherwise
        return IGNORED


class PluginInitJob(unohelper.Base, XJob):
    def __init__(self, ctx):
        self.ctx = ctx

    def execute(self, args):
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)

        model = desktop.getCurrentComponent()
        controller = model.getCurrentController()
        context_interceptor = ContextInterceptor(self.ctx)
        controller.registerContextMenuInterceptor(context_interceptor)


class MenuHandler(unohelper.Base, XInitialization, XDispatchProvider, XDispatch):
    def __init__(self, ctx):
        self.ctx = ctx

    def initialize(self, args):
        pass

    def queryDispatch(self, url, target_frame_name, search_flags):
        if url.Protocol == "se.commonsmachinery.extensions.paste_with_credit.Menu:":
            return self
        return None

    def queryDispatches(self, requests):
        dispatches = [self.queryDispatch(r.FeatureURL, r.FrameName, r.SearchFlags) for r in requests]
        return dispatches

    def dispatch(self, url, args):
        if url.Protocol == "se.commonsmachinery.extensions.paste_with_credit.Menu:":
            if url.Path == "CopyWithMetadata":
                job = CopyWithMetadataJob(self.ctx)
                job.trigger(None)

    def addStatusListener(self, control, url):
        pass

    def removeStatusListener(self, control, url):
        pass


g_ImplementationHelper = unohelper.ImplementationHelper()

g_ImplementationHelper.addImplementation(
    PasteWithCreditJob,
    "se.commonsmachinery.extensions.paste_with_credit.PasteWithCreditJob",
    ("com.sun.star.task.Job",)
)

g_ImplementationHelper.addImplementation(
    InsertCreditsJob,
    "se.commonsmachinery.extensions.paste_with_credit.InsertCreditsJob",
    ("com.sun.star.task.Job",)
)

g_ImplementationHelper.addImplementation(
    CopyWithMetadataJob,
    "se.commonsmachinery.extensions.paste_with_credit.CopyWithMetadataJob",
    ("com.sun.star.task.Job",)
)

g_ImplementationHelper.addImplementation(
    PluginInitJob,
    "se.commonsmachinery.extensions.paste_with_credit.PluginInitJob",
    ("com.sun.star.task.Job",)
)

g_ImplementationHelper.addImplementation(
    MenuHandler,
    "se.commonsmachinery.extensions.paste_with_credit.MenuHandler",
    ("com.sun.star.frame.ProtocolHandler",)
)

if __name__ == "__main__":
    import sys
    import time

    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", localContext)

    # connect to the running office, start as:
    #     soffice "--accept=socket,host=localhost,port=2002;urp;" --writer
    ctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    smgr = ctx.ServiceManager

    cmd = sys.argv[1]
    if cmd == 'paste':
        job = PasteWithCreditJob(ctx)
        job.trigger(None)

    elif cmd == 'copy':
        job = CopyWithMetadataJob(ctx)
        job.trigger(None)

        if job.clip_owner:
            print('took clipboard ownership')
            while job.clip_owner.is_owner:
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    print("I'm sorry Dave, I can't let you do that.")
                    print("Copy something else to make the script exit.")
            print("lost clipboard ownership")
        else:
            print('could not get clipboard ownership, probably no image selected')

    elif cmd == 'credit':
        job = InsertCreditsJob(ctx)
        job.trigger(None)

    else:
        print("unknown command", cmd)

    # Python-UNO bridge workaround: call a synchronous method, before the python
    # process exits to sync the remote-bridge cache, otherwise an async call
    # may not terminate properly.
    ctx.ServiceManager
