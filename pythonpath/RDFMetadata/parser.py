# parser - parse RDF/XML into model objects
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Peter Liljenberg <peter@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

import xml.dom

from . import model, domrepr, namespaces

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

class RDFXMLError(Exception):
    def __init__(self, msg, element = None):
        if element:
            msg += '\nElement: {0}'.format(element)

        self.element = element
        super(RDFXMLError, self).__init__(msg)


def parse_RDFXML(doc, root_element, strict = True):
    repr_root = domrepr.Root(doc, root_element)
    return repr_root.parse_into_model(strict = strict)


class RDFXMLParser(object):
    """Parse RDFXML, generating domrepr objects.

    This class is only to be used by domrepr, not directly.
    """

    def __init__(self, repr_root, strict = True):
        self.repr_root = repr_root
        self.strict = strict


    def parse_node_element_list(self, parent, element, top_level = False):
        """7.2.10: http://www.w3.org/TR/rdf-syntax-grammar/#nodeElementList

        nodeElementList: ws* (nodeElement ws* )*
        """

        for el in iter_subelements(element):
            if is_rdf_element(el, 'Description'):
                self.parse_node_element(parent, el, top_level)
            else:
                # Only use typed nodes when in rdf:RDF or deeper
                if not top_level or parent.root_element_is_rdf:
                    self.parse_node_element(parent, el, top_level)


    def parse_node_element(self, parent, element, top_level = False):
        """7.2.11: http://www.w3.org/TR/rdf-syntax-grammar/#nodeElement

        nodeElement:
          start-element(URI == nodeElementURIs
              attributes == set((idAttr | nodeIdAttr | aboutAttr )?, propertyAttr*))
          propertyEltList
          end-element()
        """
        
        ns = parent.get_child_ns(element)

        if is_rdf_element(element, 'Description'):
            typed_node = False
            repr = domrepr.Repr(domrepr.DescriptionNode(self.repr_root, element, ns))
        else:
            typed_node = True
            repr = domrepr.Repr(domrepr.TypedNode(self.repr_root, element, ns))

        # Check what kind of node this is by presence of rdf:ID,
        # rdf:nodeID or rdf:about

        fragment_id = element.getAttributeNS(RDF_NS, 'ID')
        node_id = element.getAttributeNS(RDF_NS, 'nodeID')
        about = element.getAttributeNS(RDF_NS, 'about')

        if fragment_id:
            # TODO: turn ID into an about
            assert False, 'not implemented yet'
            return None

        if node_id:
            if self.strict and about:
                raise RDFXMLError('specifying rdf:nodeID on a non-blank node', element)

            uri = model.NodeID(node_id)
            event = model.BlankNodeReprAdded(parent = parent,
                                             repr = repr,
                                             id = uri)

        elif about:
            uri = about
            event = model.ResourceNodeReprAdded(parent = parent,
                                                repr = repr,
                                                uri = uri)

        else:
            if top_level:
                # treat this as an empty rdf:about
                uri = ""
                event = model.ResourceNodeReprAdded(parent = parent,
                                                    repr = repr,
                                                    uri = uri)

            else:
                # internally generated node ID
                uri = model.NodeID(None)
                event = model.BlankNodeReprAdded(parent = parent,
                                                 repr = repr,
                                                 id = uri)

        # Tell model about the new node
        self.repr_root.notify_observers(event)


        if typed_node:
            # Generate the equivalent of a <rdf:type rdf:resource="..." />
            # predicate.  This can't use the same Repr as above,
            # since that would cause the type resource node to pick up
            # all the predicates of the actual resource node.

            type_repr = domrepr.Repr(domrepr.ImpliedTypeProperty(
                    self.repr_root, element, ns))

            type_uri = get_element_uri(element)
            
            # Tell model about the implied new node
            self.repr_root.notify_observers(
                event = model.ResourceNodeReprAdded(parent = parent,
                                                    repr = type_repr,
                                                    uri = type_uri))

            # Tell node about the predicate
            repr.notify_observers(
                model.PredicateNodeReprAdded(
                    parent = parent,
                    repr = type_repr,
                    predicate_uri = model.QName(RDF_NS, repr.get_rdf_ns_prefix(), 'type'),
                    object_uri = type_uri))
                    

        # TODO: parse property attributes
        
        self.parse_property_element_list(repr, element)

        return uri

        
    def parse_property_element_list(self, parent, element):
        """7.2.13: http://www.w3.org/TR/rdf-syntax-grammar/#propertyEltList

        propertyEltList: ws* (propertyElt ws* ) *
        """
        
        for el in iter_subelements(element):
            # TODO: filter out all rdf: elements?

            self.parse_property_element(parent, el)

            
    def parse_property_element(self, parent, element, reparsing = False):
        """7.2.14: http://www.w3.org/TR/rdf-syntax-grammar/#propertyElt

        propertyElt:
           resourcePropertyElt |
           literalPropertyElt |
           parseTypeLiteralPropertyElt |
           parseTypeResourcePropertyElt |
           parseTypeCollectionPropertyElt |
           parseTypeOtherPropertyElt |
           emptyPropertyElt

        This code does not handle reification.

        If reparsing is True, then a property element is updating
        itself after its attributes or contents changed and all
        notifications should reflect that.  parent is then really the
        existing property repr, but that's fine since it will have the
        right namespace setup and will take care of the notifications.
        """


        # Figure out what kind of object this predicate point to.

        # TODO: Step 1: check parseType

        # Step 2: no parseType, so check what child nodes there are

        element_nodes = [n for n in element.childNodes if n.nodeType == n.ELEMENT_NODE]
        
        if element_nodes:
            return self.parse_resource_property_element(parent, element, element_nodes, reparsing)
            
        # Step 3: literal value, or empty.  Normalize into one node or none
        element.normalize()
        text_nodes = [n for n in element.childNodes if n.nodeType == n.TEXT_NODE]
        assert len(text_nodes) < 2
        
        if text_nodes:
            text = text_nodes[0].data
            self.parse_literal_property_element(parent, element, text, reparsing)
        else:
            self.parse_empty_property_element(parent, element, reparsing)


    def parse_resource_property_element(self, parent, element, subelements, reparsing):
        """7.2.15: http://www.w3.org/TR/rdf-syntax-grammar/#resourcePropertyElt

        resourcePropertyElt:
 	    start-element(URI == propertyElementURIs ), attributes == set(idAttr?))
            ws* nodeElement ws*
            end-element()
        """
        
        ns = parent.get_child_ns(element)

        if self.strict and len(subelements) > 1:
            raise RDFError('more than one sub-element in a predicate',
                           self.element)

        repr = domrepr.Repr(domrepr.ResourceProperty(self.repr_root, element, ns))
        node_uri = self.parse_node_element(repr, subelements[0])

        if reparsing:
            event = model.PredicateChangedToNodeRepr(
                old_repr = parent,
                new_repr = repr,
                object_uri = node_uri)
        else:
            event = model.PredicateNodeReprAdded(
                parent = parent,
                repr = repr,
                predicate_uri = get_element_uri(element),
                object_uri = node_uri)

        # Tell node about the new predicate repr
        parent.notify_observers(event)


    def parse_literal_property_element(self, parent, element, text, reparsing):
        """7.2.16: http://www.w3.org/TR/rdf-syntax-grammar/#literalPropertyElt

        literalPropertyElt:
 	    start-element(URI == propertyElementURIs ),
                attributes == set(idAttr?, datatypeAttr?))
            text()
            end-element()
        """

        ns = parent.get_child_ns(element)

        type_uri = element.getAttributeNS(RDF_NS, 'datatype')
        if not type_uri:
            type_uri = None
            
        # TODO: xml:lang

        repr = domrepr.Repr(domrepr.LiteralProperty(self.repr_root, element, ns))

        if reparsing:
            event = model.PredicateChangedToLiteralRepr(
                old_repr = parent,
                new_repr = repr,
                value = text,
                type_uri = type_uri)
        else:
            event = model.PredicateLiteralReprAdded(
                parent = parent,
                repr = repr,
                predicate_uri = get_element_uri(element),
                value = text,
                type_uri = type_uri)

        parent.notify_observers(event)


    def parse_empty_property_element(self, parent, element, reparsing):
        """7.2.21: http://www.w3.org/TR/rdf-syntax-grammar/#emptyPropertyElt

        emptyPropertyElt:
 	    start-element(URI == propertyElementURIs ),
                attributes == set(idAttr?, ( resourceAttr | nodeIdAttr )?, propertyAttr*))
            end-element()
        """

        ns = parent.get_child_ns(element)

        resource_uri = element.getAttributeNS(RDF_NS, 'resource')
        node_id = element.getAttributeNS(RDF_NS, 'nodeID')

        if resource_uri and node_id:
            if self.strict:
                raise RDFError('both rdf:resource and rdf:nodeID attributes',
                               element)

        # If referring to a node, notify model about the existance of these first

        if resource_uri:
            repr = domrepr.Repr(domrepr.EmptyPropertyResource(
                    self.repr_root, element, ns))

            # Tell model about the object node.  This might seem
            # weird, but remember that rdf:resource is just a
            # short-hand for a resourcePropertyElt.

            self.repr_root.notify_observers(
                event = model.ResourceNodeReprAdded(parent = parent,
                                                    repr = repr,
                                                    uri = resource_uri))
            
            if reparsing:
                event = model.PredicateChangedToNodeRepr(
                    old_repr = parent,
                    new_repr = repr,
                    object_uri = resource_uri)
            else:
                event = model.PredicateNodeReprAdded(
                    parent = parent,
                    repr = repr,
                    predicate_uri = get_element_uri(element),
                    object_uri = resource_uri)

        elif node_id:
            uri = model.NodeID(node_id)
            
            repr = domrepr.Repr(domrepr.EmptyPropertyBlankNode(
                    self.repr_root, element, ns))

            # Same as rdf:resource, rdf:nodeID is just a shorthand
            self.repr_root.notify_observers(
                event = model.BlankNodeReprAdded(parent = parent,
                                                 repr = repr,
                                                 id = uri))
            
            # Tell node about the new predicate
            if reparsing:
                event = model.PredicateChangedToNodeRepr(
                    old_repr = parent,
                    new_repr = repr,
                    object_uri = uri)
            else:
                event = model.PredicateNodeReprAdded(
                    parent = parent,
                    repr = repr,
                    predicate_uri = get_element_uri(element),
                    object_uri = uri)

        else:
            repr = domrepr.Repr(domrepr.EmptyPropertyLiteral(
                    self.repr_root, element, ns))

            if reparsing:
                event = model.PredicateChangedToLiteralRepr(
                    old_repr = parent,
                    new_repr = repr,
                    value = '',
                    type_uri = None)
            else:
                event = model.PredicateLiteralReprAdded(
                    parent = parent,
                    repr = repr,
                    predicate_uri = get_element_uri(element),
                    value = "",
                    type_uri = None)

        # Tell node about the new (or reparsed) predicate
        parent.notify_observers(event)


def iter_subelements(element):
    """Return an iterator over all child nodes that are elements"""

    for n in element.childNodes:
        if n.nodeType == n.ELEMENT_NODE:
            yield n
        
def is_rdf_element(element, name):
    """Return TRUE if this is an RDF element with the local NAME."""
    return (element.namespaceURI == RDF_NS
            and element.localName == name)
        
def get_element_uri(element):
    return model.QName(element.namespaceURI, element.prefix, element.localName)

    
