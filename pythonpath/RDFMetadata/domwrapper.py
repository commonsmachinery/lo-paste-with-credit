# domwrapper - Wrapper around minidom to notifies observers about DOM changes
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Peter Liljenberg <peter@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

from xml.dom import minidom
from functools import wraps

from . import observer

#
# DOM Events
#

class ChildAdded(observer.Event):
    """Event when a child has been added to a node.

    Parameters:

    - parent: the parent Node 
    - child: the added child Node
    - after: the child was added after this Node, or None
    """
    pass

class ChildRemoved(observer.Event):
    """Event when a child has been removed from a node.

    Parameters:

    - parent: the parent Node
    - child: the removed child Node
    """
    pass


class AttributeSet(observer.Event):
    """Event when an attribute is set (or changed, if already set).

    Parameters:

    - element: the parent Element
    - attr: the new or updated Attr 
    """
    pass

class AttributeRemoved(observer.Event): 
    """Event when an attribute is removed.

    Parameters:

    - element: the parent Element
    - attr: the removed Attr
    """
    pass

#
# Helper methods
# 

def notify(node, event):
    """Notify observers of NODE that EVENT has occurred.

    Does nothing if node hasn't been injected with an
    observer.Subject.
    """

    try:
        n = node.notify_observers
    except AttributeError:
        return

    n(event)
    

#
# DOM wrappers
#


def wrap(node):
    if hasattr(node, 'register_observer'):
        return

    subject = observer.Subject()

    # Inject the subject into the node
    node.register_observer = subject.register_observer
    node.unregister_observer = subject.unregister_observer
    node.notify_observers = subject.notify_observers


    # Overwrite the real methods with wrapper functions, keeping a
    # reference to the original methods in this scope

    #
    # Node tree manipulation on nodes that can have children
    #

    if not isinstance(node, minidom.Childless):
        insertBefore = node.insertBefore
        @wraps(insertBefore)
        def wrap_insertBefore(newChild, refChild):
            after = refChild.previousSibling
            insertBefore(newChild, refChild)
            node.notify_observers(
                ChildAdded(parent = node,
                           child = newChild,
                           after = after))

        node.insertBefore = wrap_insertBefore
            

        appendChild = node.appendChild
        @wraps(appendChild)
        def wrap_appendChild(newChild):
            after = node.lastChild
            appendChild(newChild)
            node.notify_observers(
                ChildAdded(parent = node,
                           child = newChild,
                           after = after))

        node.appendChild = wrap_appendChild

        
        replaceChild = node.replaceChild
        @wraps(replaceChild)
        def wrap_replaceChild(newChild, oldChild):
            after = oldChild.previousSibling
            replaceChild(newChild, oldChild)
            node.notify_observers(
                ChildRemoved(parent = node,
                             child = oldChild))
            node.notify_observers(
                ChildAdded(parent = node,
                           child = newChild,
                           after = after))

        node.replaceChild = wrap_replaceChild


        removeChild = node.removeChild
        @wraps(removeChild)
        def wrap_removeChild(oldChild):
            removeChild(oldChild)
            node.notify_observers(
                ChildRemoved(parent = node,
                             child = oldChild))
     
        node.removeChild = wrap_removeChild


    #
    # Attribute manipulation on elements
    #
        
    if isinstance(node, minidom.Element):

        setAttribute = node.setAttribute
        @wraps(setAttribute)
        def wrap_setAttribute(attname, value):
            setAttribute(attname, value)
            node.notify_observers(
                AttributeSet(element = node,
                             attr = node.getAttributeNode(attname)))

        node.setAttribute = wrap_setAttribute


        setAttributeNS = node.setAttributeNS
        @wraps(setAttributeNS)
        def wrap_setAttributeNS(namespaceURI, qualifiedName, value):
            setAttributeNS(namespaceURI, qualifiedName, value)
            attr = node.getAttributeNodeNS(namespaceURI,
                                           minidom._nssplit(qualifiedName)[1])
            node.notify_observers(
                AttributeSet(element = node, attr = attr))

        node.setAttributeNS = wrap_setAttributeNS



        removeAttribute = node.removeAttribute
        @wraps(removeAttribute)
        def wrap_removeAttribute(name):
            attr = node.getAttributeNode(name)
            if attr:
                removeAttribute(name)
                node.notify_observers(AttributeRemoved(element = node, attr = attr))

        node.removeAttribute = wrap_removeAttribute
              

        removeAttributeNS = node.removeAttributeNS
        @wraps(removeAttributeNS)
        def wrap_removeAttributeNS(namespaceURI, localName):
            attr = node.getAttributeNodeNS(namespaceURI, localName)
            if attr:
                removeAttributeNS(namespaceURI, localName)
                node.notify_observers(AttributeRemoved(element = node, attr = attr))

        node.removeAttributeNS = wrap_removeAttributeNS
        

        # The attribute node versions are used internally by minidom
        # and we will not use them ourselves, so don't wrap them.

