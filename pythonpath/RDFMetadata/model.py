# model - RDF model objects
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Peter Liljenberg <peter@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

"""Model RDF graphs in a way suitable for inline editing of the
underlying RDF/XML.
"""


import collections
import uuid

from . import observer

#
# Events sent to observers of the model when it updates
#

class NodeAdded(observer.Event):
    """Common base for ResourceNodeAdded and BlankNodeAdded.

    Parameter:

    - node: the new node 
    """


class ResourceNodeAdded(NodeAdded):
    """A resource node has been added to the model.

    Parameter:

    - node: the new node 
    """
    

class BlankNodeAdded(NodeAdded):
    """A blank node has been added to the model.

    Parameter:

    - node: the new node 
    """


class PredicateAdded(observer.Event):
    """A predicate has been added to the model.  Parameters:

    - predicate: the new predicate
    - node: the subject node of the predicate
    """
    pass
    
class PredicateObjectChanged(observer.Event): 
    """The object of a predicate has changed.  Parameters:

    - predicate: the predicate 
    - node: the subject node of the predicate (if received
            via the SubjectNode or the Root)
    """
    pass

class PredicateRemoved(observer.Event):
    """A predicate has been removed.  Parameters:

    - predicate: the removed predicate object
    - node: subject node of the predicate (if received
            via the SubjectNode or the Root)
    """
    pass


class NodeRemoved(observer.Event):
    """A resource or blank node has been removed from the model.

    Parameter:

    - node: the removed node
    """


class ResourceNodeRemoved(NodeRemoved):
    """A resource node has been removed from the model.

    Parameter:

    - node: the removed node
    """
    
class BlankNodeRemoved(NodeRemoved):
    """A blank node has been removed from the model.

    Parameter:

    - node: the removed node
    """

#
# Events that are sent to the model to update it when the underlying representation changes
#

class ResourceNodeReprAdded(observer.Event): pass
class BlankNodeReprAdded(observer.Event): pass
class PredicateNodeReprAdded(observer.Event): pass
class PredicateLiteralReprAdded(observer.Event): pass
class PredicateLiteralReprValueChanged(observer.Event): pass
class PredicateLiteralReprTypeChanged(observer.Event): pass


class ReprChanged(observer.Event):
    """Base class for events where the repr type has changed,
    signalled by the old repr.  Parameter:

    - old_repr: the old repr, the source of the event
    - new_repr: the new repr that the node should use
    """

class PredicateChangedToNodeRepr(ReprChanged):
    """Signaled by a property repr when its object should change to a
    node.  Parameters:

    - old_repr: the old repr, the source of the event
    - new_repr: the new repr that the node should use
    - object_uri: the URI for the referenced node
    """

class PredicateChangedToLiteralRepr(ReprChanged): 
    """Signaled by a property repr when its object should change to a
    literal.  Parameters:

    - old_repr: the old repr, the source of the event
    - new_repr: the new repr that the node should use
    - value: the literal value
    - type_uri: data type URI, or None
    """


class NodeReprRemoved(observer.Event):
    """A subject node repr has been removed from the DOM tree.

    Parameters:

    - repr: the removed Repr
    """

class PredicateReprRemoved(observer.Event):
    """A predicate representation has been removed from the DOM tree.

    Parameters:

    - repr: the removed Repr
    """
    
    
class Root(observer.Subject, collections.Mapping):
    def __init__(self, repr):
        super(Root, self).__init__()

        self.repr = repr
        self.repr.register_observer(self._on_repr_update)
        
        # There is exactly one instance for each URI or nodeID
        self.resource_nodes = {}
        self.blank_nodes = {}


    def _on_repr_update(self, event):
        if isinstance(event, ResourceNodeReprAdded):
            node = self._get_resource_node(event.uri)
        
        elif isinstance(event, BlankNodeReprAdded):
            node = self._get_blank_node(event.id)

        else:
            return

        node._add_repr(event.repr)
        

    def _on_node_update(self, event):
        if isinstance(event, NodeRemoved):
            node = event.node
            node.unregister_observer(self._on_node_update)
            if isinstance(node, ResourceNode):
                del self.resource_nodes[node.uri]
            else:
                del self.blank_nodes[node.uri]

        # Pass on the event to allow model users to choose
        # whether to listen to root updates or node updates
        self.notify_observers(event)


    def _get_resource_node(self, uri):
        """Return a ResourceNode for uri, creating one if it doesn't exist.
        """

        try:
            node = self.resource_nodes[uri]
        except KeyError:
            node = ResourceNode(self, uri)
            self.resource_nodes[uri] = node
            node.register_observer(self._on_node_update)
            self.notify_observers(ResourceNodeAdded(node = node))

        return node


    def _get_blank_node(self, id):
        """Return a BlankNode for id, creating one if it doesn't exist.
        """

        try:
            node = self.blank_nodes[id]
        except KeyError:
            node = BlankNode(self, id)
            self.blank_nodes[id] = node
            node.register_observer(self._on_node_update)
            self.notify_observers(BlankNodeAdded(node = node))

        return node


    def _get_node(self, uri):
        """Return either a blank node or a resource node, depending on the type of URI.
        """
        
        if isinstance(uri, NodeID):
            return self._get_blank_node(uri)
        else:
            return self._get_resource_node(uri)


    def __str__(self):
        s = '\n'.join(map(str, self.resource_nodes.values()))
        s += '\n'
        s += '\n'.join(map(str, self.blank_nodes.values()))
        return s

    #
    # Support read-only Mapping interface to access the top subjects
    #
        
    def __getitem__(self, key):
        return self.resource_nodes[key]

    def __iter__(self):
        return iter(self.resource_nodes)

    def __len__(self):
        return len(self.resource_nodes)
    

class URI(object):
    """Base class for representing different kinds of URIs.

    Must be immutable (TODO: figure out decorators for that.)
    """

    def __init__(self, uri):
        self.uri = uri

    def __cmp__(self, other):
        return cmp(self.uri, str(other))

    def __hash__(self):
        return hash(self.uri)
    
    def __str__(self):
        return self.uri
    

class QName(URI):
    """A fully qualified name, used mainly by predicates.

    Keeps track of all the components of the name, but behaves like an
    URI string otherwise.

    """

    def __init__(self, ns_uri, ns_prefix, local_name):
        self.ns_uri = ns_uri
        self.ns_prefix = ns_prefix
        self.local_name = local_name
        if ns_prefix:
            self.tag_name = ns_prefix + ':' + local_name
        else:
            self.tag_name = local_name
        super(QName, self).__init__(ns_uri + local_name)

    def __eq__(self, other):
        if isinstance(other, QName):
            return self.ns_uri == other.ns_uri and \
                   self.ns_prefix == other.ns_prefix and \
                   self.local_name == other.local_name

    def __repr__(self):
        return '{0.__class__.__name__}("{0.ns_uri}", "{0.ns_prefix}", "{0.local_name}")'.format(self)


class NodeID(URI):
    """Used for the ID of a blank node.

    This isn't really an URI, but it's easier on users of the model if
    they can easily refer to it as that.
    """
    def __init__(self, node_id):
        if node_id:
            self.node_id = node_id
            self.external = True
        else:
            self.node_id = str(uuid.uuid1())
            self.external = False

        super(NodeID, self).__init__('_:' + self.node_id)
        
    def __repr__(self):
        if self.external:
            return '{0.__class__.__name__}("{0.node_id}")'.format(self)
        else:
            return '{0.__class__.__name__}(None)'.format(self)


class Node(observer.Subject, object):
    def __init__(self, root):
        super(Node, self).__init__()
        self.root = root


class SubjectNode(Node, collections.Sequence):

    def __init__(self, root, uri):
        super(SubjectNode, self).__init__(root)

        self.uri = uri
        self.reprs = []
        self.predicates = []
        
    def _add_repr(self, repr):
        assert repr not in self.reprs
        self.reprs.append(repr)
        repr.register_observer(self._on_repr_update)


    def _on_repr_update(self, event):
        if isinstance(event, PredicateNodeReprAdded):
            node = self.root._get_node(event.object_uri)
            self._add_predicate(event.repr, event.predicate_uri, node)

        elif isinstance(event, PredicateLiteralReprAdded):
            node = LiteralNode(self.root, event.repr, event.value, event.type_uri)
            self._add_predicate(event.repr, event.predicate_uri, node)

        elif isinstance(event, NodeReprRemoved):
            for r in self.reprs:
                if r.is_event_source(event):
                    self._repr_removed(r)


    def _add_predicate(self, repr, uri, object):
        pred = Predicate(self.root, repr, uri, object)
        
        self.predicates.append(pred)
        self.notify_observers(PredicateAdded(node = self, predicate = pred))

        # Listen on predicate model updates
        pred.register_observer(self._on_predicate_update)


    def _repr_removed(self, r):
        r.unregister_observer(self._on_repr_update)
        self.reprs.remove(r)
        if not self.reprs and not self.predicates:
            # No more references to us, so we disappear.
            self.notify_observers(self.REMOVED_EVENT(node = self))
            self.root = None


    def _on_predicate_update(self, event):
        if isinstance(event, PredicateRemoved):
            # This must be a predicate of ours
            self.predicates.remove(event.predicate)
            event.predicate.unregister_observer(self._on_predicate_update)

        # Pass on the event to allow model users to choose
        # whether to listen to node updates or predicate updates
        event.node = self
        self.notify_observers(event)

        if isinstance(event, PredicateRemoved):
            if not self.reprs and not self.predicates:
                # No more references to us, so we disappear (but not before
                # passing on the PredicateRemoved that triggered this
                self.notify_observers(self.REMOVED_EVENT(node = self))
                self.root = None


    def add_predicate_literal(self, qname, value = '', type_uri = None):
        # This must be true, right?
        assert self.reprs

        self.reprs[0].add_predicate_literal(self, qname, value, type_uri)

    def add_predicate_blank(self, qname, node_id=None):
        # This must be true, right?
        assert self.reprs

        self.reprs[0].add_predicate_blank(self, qname, node_id)

    #
    # Support read-only sequence interface to access the predicates
    #
        
    def __getitem__(self, item):
        return self.predicates[item]

    def __iter__(self):
        return iter(self.predicates)

    def __len__(self):
        return len(self.predicates)



class ResourceNode(SubjectNode):
    REMOVED_EVENT = ResourceNodeRemoved

    def __str__(self):
        s = '# ResourceNode({0})\n'.format(self.uri)

        for pred in self.predicates:
            s += '<{0}>\t{1} .\n'.format(self.uri, pred)

        return s

    def __repr__(self):
        return '<ResourceNode {0} at 0x{1:#x}>'.format(self.uri, id(self))


class BlankNode(SubjectNode):
    REMOVED_EVENT = BlankNodeRemoved

    def __str__(self):
        s = '# BlankNode({0})\n'.format(self.uri)

        for pred in self.predicates:
            s += '{0}\t{1} .\n'.format(self.uri, pred)

        return s

    def __repr__(self):
        return '<BlankNode {0} at 0x{1:#x}>'.format(self.uri, id(self))


class LiteralNode(Node):
    def __init__(self, root, repr, value, type_uri = None):
        super(LiteralNode, self).__init__(root)
        self.repr = repr
        self.value = value
        self.type_uri = type_uri

        repr.register_observer(self._on_repr_update)

    def set_value(self, value):
        self.repr.set_literal_value(value)


    def set_type_uri(self, type_uri):
        self.repr.set_datatype(type_uri)

        
    def _on_repr_update(self, event):
        if isinstance(event, PredicateLiteralReprValueChanged):
            assert self.repr.is_event_source(event)
            self.value = event.value

        elif isinstance(event, PredicateLiteralReprTypeChanged):
            assert self.repr.is_event_source(event)
            self.type_uri = event.type_uri
            

class Predicate(observer.Subject, object):
    def __init__(self, root, repr, uri, object):
        super(Predicate, self).__init__()

        self.root = root
        self.repr = repr
        self.uri = uri
        self.object = object

        repr.register_observer(self._on_repr_update)

        # As a special case, also listen on updates to literal nodes
        # so we can propagate changes in its value to model observers
        if isinstance(object, LiteralNode):
            object.repr.register_observer(self._on_object_repr_update)

    def remove(self):
        self.repr.remove()

    def _on_repr_update(self, event):
        if isinstance(event, PredicateReprRemoved):
            assert self.repr.is_event_source(event)

            # Just signal and let the SubjectNode remove us
            self.notify_observers(PredicateRemoved(predicate = self))
            self.root = None

            self.repr.unregister_observer(self._on_repr_update)
            self.repr = None

            if isinstance(self.object, LiteralNode):
                self.object.repr.unregister_observer(self._on_object_repr_update)

        elif isinstance(event, PredicateChangedToLiteralRepr):
            if isinstance(self.object, LiteralNode):
                self.object.repr.unregister_observer(self._on_object_repr_update)

            self.object = LiteralNode(self.root, event.new_repr, event.value, event.type_uri)
            self.object.repr.register_observer(self._on_object_repr_update)

            self._change_repr(event.new_repr)
            self.notify_observers(PredicateObjectChanged(
                    predicate = self, object = self.object))

        elif isinstance(event, PredicateChangedToNodeRepr):
            if isinstance(self.object, LiteralNode):
                self.object.repr.unregister_observer(self._on_object_repr_update)

            self.object = self.root._get_node(event.object_uri)
            self._change_repr(event.new_repr)
            self.notify_observers(PredicateObjectChanged(
                    predicate = self, object = self.object))
            

    def _change_repr(self, repr):
        self.repr.unregister_observer(self._on_repr_update)
        self.repr = repr
        self.repr.register_observer(self._on_repr_update)

    def _on_object_repr_update(self, event):
        if (isinstance(event, PredicateLiteralReprValueChanged)
            or isinstance(event, PredicateLiteralReprTypeChanged)):
            assert self.object.repr.is_event_source(event)
            self.notify_observers(
                PredicateObjectChanged(
                    predicate = self, object = self.object))


    def __str__(self):
        if isinstance(self.object, LiteralNode):
            if self.object.type_uri:
                return '<{0}>\t"{1}"^^<{2}>'.format(
                    self.uri, self.object.value, self.object.type_uri)
            else:
                return '<{0}>\t"{1}"'.format(self.uri, self.object.value)
        elif isinstance(self.object, ResourceNode):
            return '<{0}>\t<{1}>'.format(self.uri, self.object.uri)
        elif isinstance(self.object, BlankNode):
            return '<{0}>\t{1}'.format(self.uri, self.object.uri)
        else:
            return '<{0}>\t""'.format(self.uri)

    def __repr__(self):
        return '<Predicate {0} at 0x{1:#x}>'.format(self.uri, id(self))
