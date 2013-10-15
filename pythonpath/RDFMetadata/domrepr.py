# domrepr - Link from RDF model objects to underlying DOM representation
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Peter Liljenberg <peter@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

import sys
import xml.dom

from . import model, namespaces, observer
from . import domwrapper

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"


class UnsupportedFunctionError(Exception):
    def __init__(self, func, obj):
        super(Exception, self).__init__('{0} unsupported on {1}'.format(func, obj))


#
# Internal events
#

class NodeUnlinked(observer.Event):
    """A node has been unlinked from the DOM tree.  Parameters:

    - node: the unlinked node
    """
    pass


#
# DOM Representation classes
#
        
class Root(observer.Subject, object):
    """Representation for the root RDF element.
    """

    def __init__(self, doc, element):
        super(Root, self).__init__()
        
        domwrapper.wrap(element)

        self.doc = doc
        self.element = element
        self.namespaces = namespaces.Namespaces(None, element)

        self.element.register_observer(self._on_dom_update)

        # Necessary to know when adding top-level resources
        self.root_element_is_rdf = is_rdf_element(element, 'RDF')

        # Some circular dependencies between models.  Might resolve
        # that later, but I'm wary about adding too much stuff into
        # these classes and this module
        from . import parser
        self.parser = parser.RDFXMLParser(self)

    def parse_into_model(self, strict = True):
        """Return a new model.Root object that contains all
        nodes and predicates under this DOM root node.
        """

        # Create the model, which will add an observer that reacts
        # to parse events 
        model_root = model.Root(self)

        # Only do strict parsing on original document, and be forgiving
        # on later DOM updates
        self.parser.strict = strict
        self.parser.parse_node_element_list(self, self.element, True)
        self.parser.strict = False

        return model_root

    def get_child_ns(self, element):
        return namespaces.Namespaces(self.namespaces, element)

    def get_ns_prefix(self, uri, preferred_prefix):
        return self.repr.namespaces.get_prefix(uri, preferred_prefix)

    def dump(self):
        self.element.writexml(sys.stderr)

    def is_event_source(self, event):
        return event.repr is self

    def _on_dom_update(self, event):
        if isinstance(event, domwrapper.ChildAdded):
            assert event.parent is self.element
            self.parser.parse_node_element(self, event.child, top_level = True)

        elif isinstance(event, domwrapper.ChildRemoved):
            assert event.parent is self.element
            if event.child.nodeType == event.child.ELEMENT_NODE:
                # Send a notification to the Repr of that node that it
                # was unlinked, and let it recurse
                domwrapper.notify(event.child, NodeUnlinked(node = event.child))


class Repr(observer.Subject, object):
    """Intermediate object for the representation of a node.

    This is needed since operations that change data may also change
    the type of the representation.
    """

    def __init__(self, repr):
        super(Repr, self).__init__()
        self.repr = None
        self._set_repr(repr)

        # It helps having the root here too, and that one won't change
        self.root = repr.root

    def get_child_ns(self, element):
        return self.repr.get_child_ns(element)

    def get_ns_prefix(self, uri, preferred_prefix):
        return self.repr.get_ns_prefix(uri, preferred_prefix)

    def get_rdf_ns_prefix(self):
        return self.repr.get_rdf_ns_prefix()

    def is_event_source(self, event):
        return event.repr is self.repr

    def set_literal_value(self, text):
        self._set_repr(self.repr.set_literal_value(text))

    def set_datatype(self, type_uri):
        self._set_repr(self.repr.set_datatype(type_uri))

    def add_predicate_literal(self, node, qname, value, type_uri):
        self._set_repr(self.repr.add_predicate_literal(node, qname, value, type_uri))

    def add_predicate_blank(self, node, qname, node_id=None):
        self._set_repr(self.repr.add_predicate_blank(node, qname, node_id))

    def remove(self):
        """Remove this repr from the DOM tree.
        """
        self._set_repr(self.repr.remove())

    def dump(self):
        self.repr.element.writexml(sys.stderr)

    def _set_repr(self, repr):
        if repr is self.repr:
            return

        if self.repr:
            self.repr.unregister_observer(self._on_repr_update)

        self.repr = repr

        if self.repr:
            self.repr.register_observer(self._on_repr_update)

    def _on_repr_update(self, event):
        # Just pass on the event
        self.notify_observers(event)
        
            

class TypedRepr(observer.Subject, object):
    def __init__(self, root, element, namespaces):
        super(TypedRepr, self).__init__()
        
        domwrapper.wrap(element)

        self.root = root
        self.element = element
        self.namespaces = namespaces

        self.element.register_observer(self._on_dom_update)

    def to(self, cls):
        return cls(self.root, self.element, self.namespaces)

    def set_literal_value(self, text):
        raise UnsupportedFunctionError('set_literal_value', self)

    def set_datatype(self, type_uri):
        raise UnsupportedFunctionError('set_datatype', self)

    def add_predicate_literal(self, node, qname, value, type_uri):
        raise UnsupportedFunctionError('add_predicate_literal', self)

    def add_predicate_blank(self, node, qname, node_id=None):
        raise UnsupportedFunctionError('add_predicate_blank', self)

    def remove(self):
        raise UnsupportedFunctionError('remove', self)

    def get_rdf_ns_prefix(self):
        return self.namespaces.get_prefix(RDF_NS, 'rdf')

    def get_child_ns(self, element):
        return namespaces.Namespaces(self.namespaces, element)

    def add_namespace(self, qname):
        prefix = self.namespaces.get_prefix(qname.ns_uri, qname.ns_prefix)
        if prefix == qname.ns_prefix:
            return qname
        else:
            return model.QName(qname.ns_uri, prefix, qname.local_name)

    def _on_dom_update(self, event):
        pass


class ElementNode(TypedRepr):
    """http://www.w3.org/TR/rdf-syntax-grammar/#nodeElement

    Not instantiated directly.
    """
    
    def add_predicate_literal(self, node, qname, value, type_uri):
        assert isinstance(node, model.SubjectNode)
        
        # Build XML:
        # <ns:name rdf:datatype="type_uri">value</ns:name>

        qname = self.add_namespace(qname)
        element = self.root.doc.createElementNS(qname.ns_uri, qname.tag_name)

        if type_uri:
            element.setAttributeNS(
                RDF_NS, self.get_rdf_ns_prefix() + ':datatype',
                type_uri)

        if value:
            element.appendChild(self.root.doc.createTextNode(value))

        # Add the child, trigger a ChildAdded event
        self.element.appendChild(element)
        return self

    def add_predicate_blank(self, node, qname, node_id=None):
        assert isinstance(node, model.SubjectNode)

        # Build XML:
        # <ns:name><rdf:Description rdf:nodeID="node_id"/></ns:name>

        qname = self.add_namespace(qname)
        element = self.root.doc.createElementNS(qname.ns_uri, qname.tag_name)

        description_node = self.root.doc.createElementNS(RDF_NS, "Description")
        if node_id:
            description_node.setAttributeNS(
                RDF_NS, self.get_rdf_ns_prefix() + ':nodeID',
                node_id)

        element.appendChild(description_node)

        # Add the child, trigger a ChildAdded event
        self.element.appendChild(element)
        return self

    def _on_dom_update(self, event):
        if isinstance(event, domwrapper.ChildAdded):
            assert event.parent is self.element
            if event.child.nodeType == event.child.ELEMENT_NODE:
                self._parse_new_element(event.child)

        elif isinstance(event, domwrapper.ChildRemoved):
            assert event.parent is self.element
            if event.child.nodeType == event.child.ELEMENT_NODE:
                # Send a notification to the Repr of that node that it
                # was unlinked, and let it recurse
                domwrapper.notify(event.child, NodeUnlinked(node = event.child))

        elif isinstance(event, NodeUnlinked):
            assert event.node is self.element
            self._unlinked()


    def _parse_new_element(self, element):
        self.root.parser.parse_property_element(self, element)

    def _unlinked(self):
        # Tell any children about this first to unlink predicates
        for el in iter_subelements(self.element):
            domwrapper.notify(el, NodeUnlinked(node = el))

        # Then we can unlink ourselves
        self.notify_observers(model.NodeReprRemoved(repr = self))


class DescriptionNode(ElementNode):
    """http://www.w3.org/TR/rdf-syntax-grammar/#nodeElement
    (when the name is rdf:Description)

    Represents:

      - ResourceNode (without rdf:nodeID)
      - BlankNode (with rdf:nodeID)
    """
    pass


class TypedNode(ElementNode):
    """http://www.w3.org/TR/rdf-syntax-grammar/#nodeElement
    (when the name is NOT rdf:Description)

    Represents:

      - ResourceNode (without rdf:nodeID)
      - BlankNode (with rdf:nodeID)
    """
    pass


class ImpliedTypeProperty(TypedRepr):
    """http://www.w3.org/TR/rdf-syntax-grammar/#nodeElement
    (when the name is NOT rdf:Description)

    Represents:

      - Predicate (for the generated rdf:type predicate)
      - ResourceNode (for the generated rdf:type object)
    """


    def remove(self):
        # This is really tricky, since we have to go from this:
        #   <ns:Type...><ns:pred... />...</ns:Type>
        # to this:
        #   <rdf:Description><ns:pred... />...</rdf:Description>

        # DOM doesn't support renaming elements, so we have to create
        # a new element and move over the contents of the old one.
        # Finally that is unlinked, and the new one is put in place
        # instead.

        element = self.root.doc.createElementNS(
            RDF_NS, self.get_rdf_ns_prefix() + ':Description')

        # Copy attributes 
        attrs = self.element.attributes
        for i in range(attrs.length):
            attr = attrs.item(i)
            element.setAttributeNS(attr.namespaceURI, attr.name, attr.value)

        # Move children (triggering DOM removal notifications)
        while True:
            child = self.element.firstChild
            if child is None:
                break

            self.element.removeChild(child)
            element.appendChild(child)

        # Unlink ourselves, which will trigger any DOM notifications
        # on attributes

        parent = self.element.parentNode
        parent.removeChild(self.element)

        # Add the new node to the tree, triggering the final batch
        # of notifications
        parent.appendChild(element)


    def _on_dom_update(self, event):
        if isinstance(event, NodeUnlinked):
            assert event.node is self.element
            self._unlinked()

    def _unlinked(self):
        # The predicate is gone, as well as the type resource
        self.notify_observers(model.PredicateReprRemoved(repr = self))
        self.notify_observers(model.NodeReprRemoved(repr = self))


class Property(TypedRepr):
    """7.2.14: http://www.w3.org/TR/rdf-syntax-grammar/#propertyElt

    propertyElt:
       resourcePropertyElt |
       literalPropertyElt |
       parseTypeLiteralPropertyElt |
       parseTypeResourcePropertyElt |
       parseTypeCollectionPropertyElt |
       parseTypeOtherPropertyElt |
       emptyPropertyElt

    This is not instansiated directly.
    """

    def _reparse(self):
        self.root.parser.parse_property_element(self, self.element, reparsing = True)

        # This will always result in a new repr, so stop listening to
        # element events
        self.element.unregister_observer(self._on_dom_update)

        

class ResourceProperty(Property):
    """http://www.w3.org/TR/rdf-syntax-grammar/#resourcePropertyElt

    Represents:

      - Predicate
    """

    def remove(self):
        parent = self.element.parentNode
        parent.removeChild(self.element)
        return self

    def _on_dom_update(self, event):
        if isinstance(event, domwrapper.ChildRemoved):
            assert event.parent is self.element
            child = event.child

            # We only care about elements being removed, text nodes
            # can come and go as they wish
            if child.nodeType == child.ELEMENT_NODE:
                # Tell child that it is unlinked
                domwrapper.notify(child, NodeUnlinked(node = child))
                
                self._reparse()

        elif isinstance(event, domwrapper.ChildAdded):
            assert False, 'not implemented yet'

        elif isinstance(event, domwrapper.AttributeSet):
            assert False, 'not implemented yet'

        elif isinstance(event, domwrapper.AttributeRemoved):
            assert False, 'not implemented yet'

        elif isinstance(event, NodeUnlinked):
            assert event.node is self.element

            self.notify_observers(model.PredicateReprRemoved(repr = self))

            # We must also notify down, telling the node it's repr has been unlinked
            for el in iter_subelements(self.element):
                domwrapper.notify(el, NodeUnlinked(node = el))



class LiteralProperty(Property):
    """http://www.w3.org/TR/rdf-syntax-grammar/#literalPropertyElt

    Represents:

      - Predicate (always)
      - LiteralNode (always)
    """

    def set_datatype(self, type_uri):
        if type_uri:
            self.element.setAttributeNS(
                RDF_NS, self.get_rdf_ns_prefix() + ':datatype',
                type_uri)
        else:
            try:
                self.element.removeAttributeNS(RDF_NS, 'datatype')
            except xml.dom.NotFoundErr:
                pass
            
        return self


    def set_literal_value(self, text):
        # Drop old content first
        while True:
            n = self.element.firstChild
            if n is None:
                break
            self.element.removeChild(n)

        if text:
            # Set new
            self.element.appendChild(self.root.doc.createTextNode(text))
            return self
        else:
            # No more content
            return self.to(EmptyPropertyLiteral)


    def remove(self):
        parent = self.element.parentNode
        parent.removeChild(self.element)
        return self
        

    def _on_dom_update(self, event):
        if isinstance(event, domwrapper.ChildRemoved):
            self._update_text()

        elif isinstance(event, domwrapper.ChildAdded):
            node = event.child
            if node.nodeType == node.TEXT_NODE:
                self._update_text()
            else:
                # Turning into something else...
                self._reparse()

        elif isinstance(event, domwrapper.AttributeSet):
            if (event.attr.namespaceURI == RDF_NS
                and event.attr._get_localName() == 'datatype'):
                self._update_type(event.attr.value)

        elif isinstance(event, domwrapper.AttributeRemoved):
            if (event.attr.namespaceURI == RDF_NS
                and event.attr._get_localName() == 'datatype'):
                self._update_type(None)

        elif isinstance(event, NodeUnlinked):
            assert event.node is self.element
            self.notify_observers(model.PredicateReprRemoved(repr = self))


    def _update_text(self):
        self.element.normalize()
        text_nodes = [n for n in self.element.childNodes if n.nodeType == n.TEXT_NODE]
        assert len(text_nodes) <= 1
        
        if text_nodes:
            text = text_nodes[0].data
        else:
            text = ''

        self.notify_observers(
            model.PredicateLiteralReprValueChanged(repr = self, value = text))
        

    def _update_type(self, type_uri):
        self.notify_observers(
            model.PredicateLiteralReprTypeChanged(repr = self, type_uri = type_uri))


class EmptyPropertyLiteral(LiteralProperty):
    """http://www.w3.org/TR/rdf-syntax-grammar/#emptyPropertyElt

    Represents:

      - Predicate (always)
      - LiteralNode (without rdf:resource or rdf:nodeID)
    """
    pass


class EmptyPropertyResource(Property):
    """http://www.w3.org/TR/rdf-syntax-grammar/#emptyPropertyElt

    Represents:

      - Predicate (always)
      - ResourceNode (with rdf:resource)
    """
    pass

    def remove(self):
        parent = self.element.parentNode
        parent.removeChild(self.element)
        return self


    def _on_dom_update(self, event):
        if isinstance(event, domwrapper.ChildAdded):
            assert False, 'not implemented yet'

        elif isinstance(event, domwrapper.AttributeSet):
            assert False, 'not implemented yet'

        elif isinstance(event, domwrapper.AttributeRemoved):
            assert False, 'not implemented yet'

        elif isinstance(event, NodeUnlinked):
            assert event.node is self.element
            self.notify_observers(model.PredicateReprRemoved(repr = self))
            self.notify_observers(model.NodeReprRemoved(repr = self))


class EmptyPropertyBlankNode(Property):
    """http://www.w3.org/TR/rdf-syntax-grammar/#emptyPropertyElt

    Represents:

      - Predicate (always)
      - BlankNode (with rdf:nodeID)
    """
    pass

    def remove(self):
        parent = self.element.parentNode
        parent.removeChild(self.element)
        return self


    def _on_dom_update(self, event):
        if isinstance(event, domwrapper.ChildAdded):
            assert False, 'not implemented yet'

        elif isinstance(event, domwrapper.AttributeSet):
            assert False, 'not implemented yet'

        elif isinstance(event, domwrapper.AttributeRemoved):
            assert False, 'not implemented yet'

        elif isinstance(event, NodeUnlinked):
            assert event.node is self.element
            self.notify_observers(model.PredicateReprRemoved(repr = self))
            self.notify_observers(model.NodeReprRemoved(repr = self))


def is_rdf_element(element, name):
    """Return TRUE if this is an RDF element with the local NAME."""
    return (element.namespaceURI == RDF_NS
            and element.localName == name)
        
    
def iter_subelements(element):
    """Return an iterator over all child nodes that are elements"""

    for n in element.childNodes:
        if n.nodeType == n.ELEMENT_NODE:
            yield n
