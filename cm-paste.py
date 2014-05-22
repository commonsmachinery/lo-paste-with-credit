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
import rdflib
import requests

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

def json2graph(jsondata):
    g = rdflib.Graph()
    for s in jsondata:
        for p in jsondata[s]:
            for o in jsondata[s][p]:
                if o["type"] == "uri":
                    obj = rdflib.URIRef(o["value"])
                elif o["type"] == "literal":
                    obj = rdflib.Literal(o["value"])
                else:
                    obj = rdflib.BNode(o["value"])
                g.add((rdflib.URIRef(s), rdflib.URIRef(p), obj))
    return g

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
            metadata = Metadata(self.ctx, model)

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
                    subject = shape.UserDefinedAttributes.getByName("cm-subject").Value
                    credit = libcredit.Credit(rdf, subject=subject)
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


from com.sun.star.ui import XContextMenuInterceptor
from com.sun.star.ui.ContextMenuInterceptorAction import IGNORED
from com.sun.star.ui.ContextMenuInterceptorAction import EXECUTE_MODIFIED
from com.sun.star.ui.ContextMenuInterceptorAction import CONTINUE_MODIFIED

class ContextInterceptor(unohelper.Base, XContextMenuInterceptor):
    def __init__ (self, ctx):
        self.ctx = ctx

    def notifyContextMenuExecute(self, event):
        menu = event.ActionTriggerContainer
        controller = event.Selection
        selection = controller.getSelection()
        model = controller.getModel()
        menu_items = []

        # Impress document controller shows up as com.sun.star.drawing.DrawingDocumentDrawView,
        # so we rely on the model to get the idea of current document type
        canPasteText = model.supportsService("com.sun.star.text.TextDocument") and \
                       selection.supportsService("com.sun.star.text.TextRanges")
        canPastePresentation = model.supportsService("com.sun.star.presentation.PresentationDocument")

        if canPasteText or canPastePresentation:
            item = menu.createInstance("com.sun.star.ui.ActionTrigger")
            item.setPropertyValue("Text", "Add image from elog.io")
            item.setPropertyValue("CommandURL", u"se.commonsmachinery.pwc.Menu:PasteWithCredit")
            menu_items.append(item)

        # selection can be None in Draw and Impress sometimes
        if selection is not None and \
           selection.supportsService("com.sun.star.text.TextGraphicObject"):
            # TextGraphicObject implicitly supports XNamed
            # (not shown in the supported service names)
            img_name = selection.getName()

            if img_name.startswith("$metadata-tag-do-not-edit$"):
                item = menu.createInstance("com.sun.star.ui.ActionTrigger")
                item.setPropertyValue("Text", "Copy with credits")
                item.setPropertyValue("CommandURL", u"se.commonsmachinery.pwc.Menu:CopyWithMetadata")
                menu_items.append(item)

        if len(menu_items) > 0:
            item_count = menu.Count

            if len(menu_items) > 1:
                separator = menu.createInstance("com.sun.star.ui.ActionTriggerSeparator")
                separator.SeparatorType = LINE
                menu_items.insert(1, separator)
            #menu.insertByIndex(item_count + 0, separator)

            for i, item in enumerate(menu_items, start=item_count):
                menu.insertByIndex(i, item)

            return CONTINUE_MODIFIED

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


from com.sun.star.lang import XInitialization
from com.sun.star.frame import XDispatch
from com.sun.star.frame import XDispatchProvider

class MenuHandler(unohelper.Base, XInitialization, XDispatchProvider, XDispatch):
    def __init__(self, ctx):
        self.ctx = ctx

    def initialize(self, args):
        pass

    def queryDispatch(self, url, target_frame_name, search_flags):
        if url.Protocol == "se.commonsmachinery.pwc.Menu:":
            return self
        return None

    def queryDispatches(self, requests):
        dispatches = [self.queryDispatch(r.FeatureURL, r.FrameName, r.SearchFlags) for r in requests]
        return dispatches

    def dispatch(self, url, args):
        if url.Protocol == "se.commonsmachinery.pwc.Menu:":
            if url.Path == "CopyWithMetadata":
                job = CopyWithMetadataJob(self.ctx)
                job.trigger(None)
            elif url.Path == "PasteWithCredit":
                job = PasteFromCatalogJob(self.ctx)
                job.trigger(None)

    def addStatusListener(self, control, url):
        pass

    def removeStatusListener(self, control, url):
        pass


from com.sun.star.awt import XContainerWindowEventHandler
from com.sun.star.lang import XServiceInfo
from com.sun.star.lang import IllegalArgumentException
from com.sun.star.uno import Exception as UnoException
from com.sun.star.beans.PropertyState import DIRECT_VALUE

class OptionsEventHandler(unohelper.Base, XContainerWindowEventHandler, XServiceInfo):
    supported_window_names = ["OptionsDialog"];
    control_names = ["TextFieldCatalog", "TextFieldUser", "TextFieldPassword"]

    def __init__(self, ctx):
        self.ctx = ctx
        self.access_leaves = ConfigurationAccess.createUpdateAccess(ctx,
            "/se.commonsmachinery.pwc.OptionsDialog/Leaves");

    def getSupportedMethodNames(self):
        return ("external_event", )

    def callHandlerMethod(self, window, event, method):
        if method == "external_event":
            return self.handle_external_event(window, event)

    def handle_external_event(self, window, event):
        method = str(event)
        if method == "ok":
            self.save_data(window);
        elif method == "back" or method == "initialize":
            self.load_data(window);
        return True

    def save_data(self, window):
        window_name = self.get_window_name(window)
        if window_name is None:
            raise IllegalArgumentException("The window is not supported by this handler", self, -1)

        for control_name in self.control_names:
            control = window.getControl(control_name);
            if control is None:
                continue

            prop = control.getModel()
            if prop is None:
                raise UnoException("Could not get XPropertySet from control.", self);

            try:
                if control_name.startswith("Text"):
                    value = prop.getPropertyValue("Text")
                elif control_name.startswith("chk"):
                    value = prop.getPropertyValue("State")
                elif control_name.startswith("lst"):
                    # TODO: add "Selected" to property keys
                    pass
            except IllegalArgumentException as e:
                print(e)
                raise IllegalArgumentException("Wrong property type.", self, -1);

            leaf = self.access_leaves.getByName(window_name)
            # TODO: use property keys to handle list values
            leaf.setPropertyValue(control_name, value)

        self.access_leaves.commitChanges()

    def load_data(self, window):
        window_name = self.get_window_name(window)
        if window_name is None:
            raise IllegalArgumentException("The window is not supported by this handler", self, -1)

        for control_name in self.control_names:
            leaf = self.access_leaves.getByName(window_name)

            value = leaf.getPropertyValue(control_name);
            control = window.getControl(control_name);
            if control is None:
                continue

            prop = control.getModel()
            if prop is None:
                raise UnoException("Could not get XPropertySet from control.", self);

            if control_name.startswith("Text"):
                prop.setPropertyValue("Text", value)
            elif control_name.startswith("chk"):
                prop.setPropertyValue("State", value)
            elif control_name.startswith("lst"):
                prop.setPropertyValue("StringItemList", value)
                value = leaf.getPropertyValue(control_name + "Selected")
                prop.setPropertyValue("SelectedItems", value)

    def get_window_name(self, window):
        if window is None:
            raise IllegalArgumentException("Method external_event requires that a window is passed as argument", self, -1)
        window_name = window.getModel().getPropertyValue("Name")

        model = window.getModel()
        if model is None:
            raise UnoException("Cannot obtain XControlModel from XWindow in method external_event.", self);

        window_name = model.getPropertyValue("Name");
        if window_name in self.supported_window_names:
            return window_name
        else:
            return None

class ConfigurationAccess(object):
    @staticmethod
    def createUpdateAccess(ctx, path):
        try:
            config = ctx.getServiceManager().createInstanceWithContext(
                "com.sun.star.configuration.ConfigurationProvider", ctx)
        except UnoException as e:
            print(e)
            return None

        args = (PropertyValue("nodepath", 0, path, DIRECT_VALUE), )
        try:
            access = config.createInstanceWithArguments("com.sun.star.configuration.ConfigurationUpdateAccess", args)
        except UnoException as e:
            print(e)
            return None

        return access


from com.sun.star.awt.MessageBoxType import MESSAGEBOX
from com.sun.star.awt.MessageBoxType import INFOBOX
from com.sun.star.awt.MessageBoxType import WARNINGBOX
from com.sun.star.awt.MessageBoxType import ERRORBOX
from com.sun.star.awt.MessageBoxType import ERRORBOX
from com.sun.star.awt.MessageBoxType import QUERYBOX
from com.sun.star.awt.MessageBoxButtons import BUTTONS_OK
from com.sun.star.awt.MessageBoxButtons import DEFAULT_BUTTON_OK

# this should be compatible with both 3.5 and 4.x
# adapted from https://wiki.openoffice.org/wiki/Python/Transfer_from_Basic_to_Python#Message_Box
def messagebox(ctx, parent, message, title, message_type, buttons):
    """ Show message in message box. """

    def check_method_parameter(ctx, interface_name, method_name, param_index, param_type):
        """ Check the method has specific type parameter at the specific position. """
        cr = ctx.getServiceManager().createInstanceWithContext("com.sun.star.reflection.CoreReflection", ctx)
        try:
            idl = cr.forName(interface_name)
            m = idl.getMethod(method_name)
            if m:
                info = m.getParameterInfos()[param_index]
                return info.aType.getName() == param_type
        except:
            pass
        return False

    toolkit = parent.getToolkit()
    older_imple = check_method_parameter(
        ctx, "com.sun.star.awt.XMessageBoxFactory", "createMessageBox",
        1, "com.sun.star.awt.Rectangle")
    if older_imple:
        msgbox = toolkit.createMessageBox(
            parent, Rectangle(), message_type, buttons, title, message)
    else:
        message_type = {
            "messbox": MESSAGEBOX,
            "infobox": INFOBOX,
            "warningbox": WARNINGBOX,
            "errorbox": ERRORBOX,
            "querybox": QUERYBOX
        }[message_type]
        msgbox = toolkit.createMessageBox(
            parent, message_type, buttons, title, message)
    n = msgbox.execute()
    msgbox.dispose()
    return n

from com.sun.star.awt import XActionListener
from com.sun.star.awt import XItemListener

class DialogActionListener(unohelper.Base, XActionListener):
    def __init__(self, job):
        self.job = job

    def actionPerformed(self, action_event):
        command = action_event.ActionCommand
        if command == "add":
            pos = self.job.dialog.getControl("SourcesListBox").getSelectedItemPos()
            source = self.job.sources[pos]
            self.job.add_source(source)
        elif command == "cancel":
            pass
        self.job.dialog.endExecute()

class ListItemListener(unohelper.Base, XItemListener):
    def __init__(self, job):
        self.job = job

    def itemStateChanged(self, item_event):
        pos = item_event.Source.getSelectedItemPos()
        if pos == -1:
            self.job.dialog.getControl("CommandButtonAdd").setEnable(False)
        else:
            self.job.dialog.getControl("CommandButtonAdd").setEnable(True)

class ListActionListener(unohelper.Base, XActionListener):
    def actionPerformed(self, item_event):
        pos = item_event.Source.getSelectedItemPos()
        if pos == -1:
            return
        source = self.job.sources[pos]

class PasteFromCatalogJob(unohelper.Base, XJobExecutor):
    def __init__(self, ctx):
        self.ctx = ctx
        self.access_leaves = ConfigurationAccess.createUpdateAccess(ctx,
            "/se.commonsmachinery.pwc.OptionsDialog/Leaves");
        self.sources = []

    def trigger(self, args):
        dialog_provider = self.ctx.getServiceManager().createInstanceWithContext("com.sun.star.awt.DialogProvider", self.ctx)
        self.dialog = dialog_provider.createDialog("vnd.sun.star.extension://se.commonsmachinery.pwc/dialogs/PasteFromCatalog.xdl")

        action_listener = DialogActionListener(self)

        control = self.dialog.getControl("CommandButtonAdd")
        control.addActionListener(action_listener)
        control.setActionCommand("add")
        #control.setEnable(False)

        control = self.dialog.getControl("CommandButtonCancel")
        control.addActionListener(action_listener)
        control.setActionCommand("cancel")

        # load settings
        leaf = self.access_leaves.getByName("OptionsDialog")
        option_catalog = leaf.getPropertyValue("TextFieldCatalog")
        option_user = leaf.getPropertyValue("TextFieldUser")
        option_password = leaf.getPropertyValue("TextFieldPassword")
        headers = {'Accept': 'application/json'}

        # get user
        try:
            r = requests.get(option_catalog + "/users/current", headers=headers,
                             auth=requests.auth.HTTPBasicAuth(option_user, option_password))
        except requests.exceptions.RequestException as e:
            self.error_message("Couldn't get user resource.\n\n{0}".format(e))
            return

        if r.status_code != 200:
            self.error_message("Couldn't get user resource.\n\n{0}".format(r.text))
            return

        user_resource = r.url

        # get list of sources
        source_list = self.dialog.getControl("SourcesListBox")
        source_list.addItemListener(ListItemListener(self))
        source_list.addActionListener(ListActionListener())

        try:
            r = requests.get(user_resource + "/sources", headers=headers,
                             auth=requests.auth.HTTPBasicAuth(option_user, option_password))
        except requests.exceptions.RequestException as e:
            self.error_message("Couldn't get sources for user.\n\n{0}".format(e))
            return

        def datekey(source):
            if "updated" in source:
                return source["updated"]
            elif "added" in source:
                return source["added"]
            raise RuntimeError("Incomplete source entry")

        raw_sources = r.json()
        raw_sources.sort(key=datekey)
        raw_sources.reverse()
        self.sources = []

        for source in raw_sources:
            cem = json2graph(source["cachedExternalMetadataGraph"])
            metadata = json2graph(source["metadataGraph"])
            resource = source["resource"]
            try:
                img_src = next(metadata[next(metadata.subjects()):rdflib.URIRef("http://catalog.commonsmachinery.se/ns#imageSrc"):])
            except StopIteration:
                # No image source, so ignore this one
                pass
            else:
                credit = libcredit.Credit(cem, subject=resource)
                credit_writer = libcredit.TextCreditFormatter()
                credit.format(credit_writer, source_depth=0)
                source_list.addItem(credit_writer.get_text(), -1)
                self.sources.append((resource, img_src, cem))

        source_list.selectItemPos(0, True)

        self.dialog.execute()
        self.dialog.dispose()

    def error_message(self, message):
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)
        frame = desktop.getCurrentFrame()
        window = frame.getContainerWindow()
        messagebox(self.ctx, window, message, "Error", "errorbox", BUTTONS_OK | DEFAULT_BUTTON_OK)

    def add_source(self, source):
        resource, img_src, cem = source

        # fetch image
        try:
            r = requests.get(img_src)
        except requests.exceptions.RequestException as e:
            self.error_message("Couldn't get image.\n\n{0}".format(e))
            return

        if r.status_code != 200:
            self.error_message("Couldn't get image.\n\n{0}".format(r.text))
            return

        # create graphic and descriptor
        img_stream = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.io.SequenceInputStream", self.ctx)
        img_stream.initialize((uno.ByteSequence(r.content),))
        graphic_provider = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.graphic.GraphicProvider", self.ctx)

        stream_property = PropertyValue()
        stream_property.Name = "InputStream"
        stream_property.Value = img_stream

        descriptor = graphic_provider.queryGraphicDescriptor((stream_property,))
        graphic = graphic_provider.queryGraphic((stream_property,))

        # also create rdf for serializing to attributes
        rdf = cem.serialize(format="xml")

        # add image+metadata
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)

        model = desktop.getCurrentComponent()
        controller = model.getCurrentController()
        img_size = descriptor.getPropertyValue("SizePixel")

        if model.supportsService("com.sun.star.text.TextDocument"):
            # Metadata is only supported in text documents
            metadata = Metadata(self.ctx, model)

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
            credit = libcredit.Credit(rdf, subject=resource)
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

            attributes = shape.UserDefinedAttributes

            attr = uno.createUnoStruct("com.sun.star.xml.AttributeData")
            attr.Value = rdf
            attributes.insertByName("cm-metadata", attr)

            attr = uno.createUnoStruct("com.sun.star.xml.AttributeData")
            attr.Value = resource
            attributes.insertByName("cm-subject", attr)

            shape.UserDefinedAttributes = attributes

            size = shape.Size
            shape.setPosition(Point(
                int((page.Width - size.Width) / 2),
                int((page.Height - size.Height) / 2))
            )
        return # add_source

g_ImplementationHelper = unohelper.ImplementationHelper()

g_ImplementationHelper.addImplementation(
    #PasteWithCreditJob,
    PasteFromCatalogJob,
    "se.commonsmachinery.pwc.PasteWithCreditJob",
    ("com.sun.star.task.Job",)
)

g_ImplementationHelper.addImplementation(
    InsertCreditsJob,
    "se.commonsmachinery.pwc.InsertCreditsJob",
    ("com.sun.star.task.Job",)
)

g_ImplementationHelper.addImplementation(
    CopyWithMetadataJob,
    "se.commonsmachinery.pwc.CopyWithMetadataJob",
    ("com.sun.star.task.Job",)
)

g_ImplementationHelper.addImplementation(
    PluginInitJob,
    "se.commonsmachinery.pwc.PluginInitJob",
    ("com.sun.star.task.Job",)
)

g_ImplementationHelper.addImplementation(
    MenuHandler,
    "se.commonsmachinery.pwc.MenuHandler",
    ("com.sun.star.frame.ProtocolHandler",)
)

g_ImplementationHelper.addImplementation(
    OptionsEventHandler,
    "se.commonsmachinery.pwc.OptionsEventHandler",
    ("com.sun.star.awt.XContainerWindowEventHandler",)
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

    elif cmd == 'catalog':
        job = PasteFromCatalogJob(ctx)
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
