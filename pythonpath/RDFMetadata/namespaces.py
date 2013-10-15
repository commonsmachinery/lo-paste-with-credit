# namespaces - handle namespaces since xml.dom.minidom doesn't
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Peter Liljenberg <peter@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.


class Namespaces(object):
    """Keep track of namespaces scope for each element
    and update it as necessary.
    """

    def __init__(self, parent, element):
        attrs = element.attributes
        assert attrs is not None, 'trying to track namespaces for non-element node'

        self.parent = parent
        self.element = element
        self.uri_prefix_map = {}

        if parent is None:
            # Grab everything up to root
            self._populate(element, None)
        else:
            # Grab everything up to parent element
            self._populate(element, parent.element)


    def _populate(self, element, stop_element):
        # Passed the root?
        if element.nodeType == element.DOCUMENT_NODE:
            return

        # Reach the parent?
        if element is stop_element:
            return
        
        # Recurse first, so that we overwrite anything added further below
        self._populate(element.parentNode, stop_element)

        attrs = element.attributes
        if attrs is None:
            return

        # Add all attributes
        for (name, value) in attrs.items():
            if name.startswith('xmlns:'):
                self.uri_prefix_map[value] = name[6:]
            elif name == 'xmlns':
                self.uri_prefix_map[value] = None
                
                
    def get_prefix(self, uri, preferred_prefix):
        """Return a prefix for URI in the current scope.

        If the URI is not known, it is added, using preferred_prefix
        if available.

        If None is returned, the URI is the default.
        """
        
        assert preferred_prefix, 'prefix must be non-empty'

        try:
            return self.uri_prefix_map[uri]
        except KeyError:
            pass


        # Recurse if we have a parent
        if self.parent:
            prefix = self.parent.get_prefix(uri, preferred_prefix)

            # If this prefix already in use for something else in this
            # scope, we must redefine the namespace here

            new_prefix = self._check_prefix(prefix)
            if new_prefix != prefix:
                prefix = new_prefix
                self.uri_prefix_map[uri] = prefix
                self.element.setAttribute('xmlns:' + prefix, uri)
            
            return prefix

        else:
            # Reached root, so add namespace to this scope and element
            prefix = self._check_prefix(preferred_prefix)
            self.uri_prefix_map[uri] = prefix
            self.element.setAttribute('xmlns:' + prefix, uri)
            return prefix


    def _check_prefix(self, preferred_prefix):
        prefix = preferred_prefix
        c = 1
        while prefix in self.uri_prefix_map.itervalues():
            c += 1
            prefix = preferred_prefix + str(c)

        return prefix
