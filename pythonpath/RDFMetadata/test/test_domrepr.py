# parser - parse RDF/XML into model objects
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Peter Liljenberg <peter@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.


import unittest
from xml.dom import minidom

# https://pypi.python.org/pypi/py-dom-xpath
import xpath

from .. import parser, model, domrepr
from .. import observer


def get_root(xml):
    """Test helper function: parse XML and return a model.Root from the
    XML root element.
    """
    doc = minidom.parseString(xml)
    return parser.parse_RDFXML(doc = doc, root_element = doc.documentElement)


class CommonTest(unittest.TestCase):
    def assertPredicate(self, pred, uri, object_class, repr_class):
        self.assertIsInstance(pred, model.Predicate)
        self.assertEqual(pred.uri, uri)
        self.assertIsInstance(pred.object, object_class)
        self.assertRepr(pred, repr_class)

    def assertRepr(self, obj, repr_class):
        self.assertIsInstance(obj.repr.repr, repr_class)


class XPathAsserts(object):
    def __init__(self, test, node):
        self.test = test
        self.node = node
        self.ctx = xpath.XPathContext(node)

    def assertNodeCount(self, count, path, node = None):
        if node is None:
            node = self.node

        r = self.ctx.find(path, node)
        self.test.assertIsInstance(r, list, "path didn't return list of nodes")
        self.test.assertEqual(len(r), count)


    def assertValue(self, expected, path, node = None):
        if node is None:
            node = self.node

        r = self.ctx.findvalues(path, node)
        self.test.assertIsInstance(r, list)
        self.test.assertEqual(len(r), 1, "path didn't return exactly one value")
        self.test.assertEqual(r[0], expected)



class TestLiteralNode(CommonTest):
    def test_change_value(self):
        r = get_root('''<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dc="http://purl.org/dc/elements/1.1/">
  <rdf:Description rdf:about="">
    <dc:title>Test title</dc:title>
  </rdf:Description>
</rdf:RDF>
''')
        
        xp = XPathAsserts(self, r.repr.element)

        pred = r[''][0]
        self.assertPredicate(pred, "http://purl.org/dc/elements/1.1/title",
                             model.LiteralNode, domrepr.LiteralProperty)
        obj = pred.object
        
        self.assertEqual(obj.value, 'Test title')
        self.assertIsNone(obj.type_uri)

        #
        # Change value
        #

        # Two events, unfortunately, since the content is first dropped,
        # then a new text node is set.
        with observer.AssertEvent(self, r,
                                  model.PredicateObjectChanged,
                                  model.PredicateObjectChanged):
            obj.set_value('new value')
        self.assertIsNone(obj.type_uri)

        # Same repr, new value
        self.assertRepr(obj, domrepr.LiteralProperty)
        xp.assertNodeCount(1, "/rdf:RDF/rdf:Description/dc:title")
        xp.assertValue("new value", "/rdf:RDF/rdf:Description/dc:title")
        xp.assertNodeCount(0, "/rdf:RDF/rdf:Description/dc:title/@rdf:datatype")

        #
        # Set type_uri
        #

        with observer.AssertEvent(self, r, model.PredicateObjectChanged):
            obj.set_type_uri('test:type')
        self.assertEqual(obj.type_uri, 'test:type')

        # Same repr, added attribute
        self.assertRepr(obj, domrepr.LiteralProperty)
        xp.assertValue("test:type", "/rdf:RDF/rdf:Description/dc:title/@rdf:datatype")

        #
        # Drop value
        #

        with observer.AssertEvent(self, r, model.PredicateObjectChanged):
            obj.set_value('')
        self.assertEqual(obj.type_uri, 'test:type')

        # New repr, no value
        self.assertRepr(obj, domrepr.EmptyPropertyLiteral)
        xp.assertValue("", "/rdf:RDF/rdf:Description/dc:title")
        xp.assertValue("test:type", "/rdf:RDF/rdf:Description/dc:title/@rdf:datatype")

        #
        # Set value again
        #

        with observer.AssertEvent(self, r, model.PredicateObjectChanged):
            obj.set_value('set again')
        self.assertEqual(obj.type_uri, 'test:type')

        # New repr, new value
        self.assertRepr(obj, domrepr.LiteralProperty)
        xp.assertValue("set again", "/rdf:RDF/rdf:Description/dc:title")
        xp.assertValue("test:type", "/rdf:RDF/rdf:Description/dc:title/@rdf:datatype")

        #
        # Drop type
        #

        with observer.AssertEvent(self, r, model.PredicateObjectChanged):
            obj.set_type_uri(None)
        self.assertIsNone(obj.type_uri)

        # Same repr, no attr
        self.assertRepr(obj, domrepr.LiteralProperty)
        xp.assertValue("set again", "/rdf:RDF/rdf:Description/dc:title")
        xp.assertNodeCount(0, "/rdf:RDF/rdf:Description/dc:title/@rdf:datatype")
        

class TestElementNode(CommonTest):
    def test_add_empty_literal_node(self):
        r = get_root('''<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dc="http://purl.org/dc/elements/1.1/">
  <rdf:Description rdf:about="">
  </rdf:Description>
</rdf:RDF>
''')
        
        xp = XPathAsserts(self, r.repr.element)

        res = r['']
        self.assertEqual(len(res), 0)

        with observer.AssertEvent(self, r, model.PredicateAdded):
            res.add_predicate_literal(
                model.QName("http://purl.org/dc/elements/1.1/", "dc", "title"))

        # Check that model updated
        self.assertEqual(len(res), 1)
        pred = res[0]
        self.assertPredicate(pred, "http://purl.org/dc/elements/1.1/title",
                             model.LiteralNode, domrepr.EmptyPropertyLiteral)
        obj = pred.object
        
        self.assertEqual(obj.value, '')
        self.assertIsNone(obj.type_uri)

        # Check that XML updated
        xp.assertNodeCount(1, "/rdf:RDF/rdf:Description/dc:title")
        xp.assertValue('', "/rdf:RDF/rdf:Description/dc:title")
        xp.assertNodeCount(0, "/rdf:RDF/rdf:Description/dc:title/@rdf:datatype")
        

    def test_add_non_empty_literal_node(self):
        r = get_root('''<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dc="http://purl.org/dc/elements/1.1/">
  <rdf:Description rdf:about="">
  </rdf:Description>
</rdf:RDF>
''')
        
        res = r['']
        self.assertEqual(len(res), 0)

        with observer.AssertEvent(self, r, model.PredicateAdded):
            res.add_predicate_literal(
                model.QName("http://purl.org/dc/elements/1.1/", "dc", "title"),
                "value", "test:type")

        # Check that model updated
        self.assertEqual(len(res), 1)
        pred = res[0]
        self.assertPredicate(pred, "http://purl.org/dc/elements/1.1/title",
                             model.LiteralNode, domrepr.LiteralProperty)
        obj = pred.object
        
        self.assertEqual(obj.value, 'value')
        self.assertEqual(obj.type_uri, 'test:type')

        # Check that XML updated
        xp = XPathAsserts(self, r.repr.element)
        xp.assertNodeCount(1, "/rdf:RDF/rdf:Description/dc:title")
        xp.assertValue('value', "/rdf:RDF/rdf:Description/dc:title")
        xp.assertNodeCount(1, "/rdf:RDF/rdf:Description/dc:title/@rdf:datatype")
        xp.assertValue('test:type', "/rdf:RDF/rdf:Description/dc:title/@rdf:datatype")
        
        
    # @observer.log_function_events
    def test_remove_literal_property(self):
        r = get_root('''<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dc="http://purl.org/dc/elements/1.1/">
  <rdf:Description rdf:about="">
    <dc:title>Test</dc:title>
  </rdf:Description>
</rdf:RDF>
''')
        
        xp = XPathAsserts(self, r.repr.element)

        res = r['']
        self.assertEqual(len(res), 1)
        p = res[0]
        
        with observer.AssertEvent(self, r, model.PredicateRemoved):
            p.remove()
            
        # Check that model updated
        self.assertEqual(len(res), 0)

        # Check that XML updated
        xp.assertNodeCount(0, "/rdf:RDF/rdf:Description/dc:title")


    # @observer.log_function_events
    def test_remove_empty_property_resource(self):
        r = get_root('''<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dc="http://purl.org/dc/elements/1.1/">
  <rdf:Description rdf:about="">
    <dc:source rdf:resource="http://test/" />
    <dc:source rdf:resource="http://test/" />
  </rdf:Description>
</rdf:RDF>
''')
        
        xp = XPathAsserts(self, r.repr.element)

        self.assertTrue("http://test/" in r)
        
        res = r['']
        self.assertEqual(len(res), 2)
        p0 = res[0]
        p1 = res[1]

        # Removing the first reference will not remove the resource node
        with observer.AssertEvent(self, r,
                                  model.PredicateRemoved):
            p0.remove()
            
        # Check that model updated
        self.assertEqual(len(res), 1)
        self.assertTrue("http://test/" in r)

        # Check that XML updated
        xp.assertNodeCount(1, "/rdf:RDF/rdf:Description/dc:source")


        # Since removing the remaining reference to this resource, it should
        # be removed from the model wholly
        with observer.AssertEvent(self, r,
                                  model.PredicateRemoved,
                                  model.ResourceNodeRemoved):
            p1.remove()

        # Check that model updated
        self.assertEqual(len(res), 0)
        self.assertTrue("http://test/" not in r)

        # Check that XML updated
        xp.assertNodeCount(0, "/rdf:RDF/rdf:Description/dc:source")


    #@observer.log_function_events
    def test_remove_resource_property(self):
        r = get_root('''<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dc="http://purl.org/dc/elements/1.1/">
  <rdf:Description rdf:about="">
    <dc:creator>
      <rdf:Description>
        <dc:title>Test</dc:title>
      </rdf:Description>
    </dc:creator>
  </rdf:Description>
</rdf:RDF>
''')
        
        xp = XPathAsserts(self, r.repr.element)

        res = r['']
        self.assertEqual(len(res), 1)
        creator = res[0]

        blank = creator.object
        self.assertEqual(len(blank), 1)
        title = blank[0]
        
        with observer.AssertEvent(
            self, r,
            (model.PredicateRemoved, { 'predicate': creator }),
            (model.PredicateRemoved, { 'predicate': title }),
            (model.BlankNodeRemoved, { 'node': blank }),
            ):
            creator.remove()
            
        # Check that model updated
        self.assertEqual(len(res), 0)
        self.assertEqual(len(r.blank_nodes), 0)

        # Check that XML updated
        xp.assertNodeCount(0, "/rdf:RDF/rdf:Description/dc:creator")


    #@observer.log_function_events
    def test_remove_typed_node_property(self):
        r = get_root('''<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dc="http://purl.org/dc/elements/1.1/"
         xmlns:cc="http://creativecommons.org/ns#">
  <rdf:Description rdf:about="">
    <dc:creator>
      <cc:Agent>
        <dc:title>Test</dc:title>
      </cc:Agent>
    </dc:creator>
  </rdf:Description>
</rdf:RDF>
''')
        # cc:Agent is an invention in Inkscape - doesn't really exist in cc:
        
        xp = XPathAsserts(self, r.repr.element)

        # There's two resources: "" and cc:Agent
        self.assertEqual(len(r), 2)

        res = r['']
        self.assertEqual(len(res), 1)
        creator = res[0]

        blank = creator.object

        # Remember the implied rdf:type property too
        self.assertEqual(len(blank), 2)
        rdftype = blank[0]
        type_node = rdftype.object
        title = blank[1]
        
        with observer.AssertEvent(
            self, r,
            (model.PredicateRemoved, { 'predicate': creator }),
            (model.PredicateRemoved, { 'predicate': title }),
            (model.PredicateRemoved, { 'predicate': rdftype }),
            (model.BlankNodeRemoved, { 'node': blank }),
            (model.ResourceNodeRemoved, { 'node': type_node}),
            ):
            creator.remove()
            
        # Check that model updated: cc:Agent should be gone now
        self.assertEqual(len(r), 1)
        self.assertEqual(len(res), 0)
        self.assertEqual(len(r.blank_nodes), 0)

        # Check that XML updated
        xp.assertNodeCount(0, "/rdf:RDF/rdf:Description/dc:creator")


    #@observer.log_function_events
    def test_remove_implied_type_property(self):
        r = get_root('''<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dc="http://purl.org/dc/elements/1.1/"
         xmlns:cc="http://creativecommons.org/ns#">
  <rdf:Description rdf:about="">
    <dc:creator>
      <cc:Agent>
        <dc:title>Test</dc:title>
      </cc:Agent>
    </dc:creator>
  </rdf:Description>
</rdf:RDF>
''')
        # cc:Agent is an invention in Inkscape - doesn't really exist in cc:
        
        xp = XPathAsserts(self, r.repr.element)

        # There's two resources: "" and cc:Agent
        self.assertEqual(len(r), 2)

        res = r['']
        self.assertEqual(len(res), 1)
        creator = res[0]

        blank = creator.object

        # Get the implied rdf:type property too
        self.assertEqual(len(blank), 2)
        rdftype = blank[0]
        self.assertPredicate(rdftype, domrepr.RDF_NS + 'type',
                             model.ResourceNode, domrepr.ImpliedTypeProperty)

        type_node = rdftype.object

        title = blank[1]
        
        with observer.AssertEvent(
            self, r,
            # Moving predicate to new rdf:Description element
            (model.PredicateRemoved, { 'predicate': title }),

            # Unlinking cc:Agent
            (model.PredicateRemoved, { 'predicate': rdftype }),
            (model.BlankNodeRemoved, { 'node': blank }),
            (model.ResourceNodeRemoved, { 'node': type_node}),

            # Which turns dc:creator temporarily into an empty literal
            (model.PredicateObjectChanged, { 'predicate': creator }),

            # The re-added node and dc:title
            model.BlankNodeAdded,
            model.PredicateAdded,

            # Finally dc:creator is again a resource property when the
            # new rdf:Description is added
            (model.PredicateObjectChanged, { 'predicate': creator }),
            ):
            rdftype.remove()
            
        # Check that model updated: cc:Agent should now be
        # rdf:Description and the type node is gone
        self.assertEqual(len(r), 1)
        self.assertEqual(len(r.blank_nodes), 1)

        self.assertEqual(len(res), 1)
        self.assertIs(creator, res[0])

        blank = creator.object

        # Just dc:title now
        self.assertEqual(len(blank), 1)
        self.assertPredicate(blank[0], 'http://purl.org/dc/elements/1.1/title',
                             model.LiteralNode, domrepr.LiteralProperty)

        # Check that XML updated
        xp.assertNodeCount(0, "/rdf:RDF/rdf:Description/dc:creator/cc:Work")
        xp.assertNodeCount(1, "/rdf:RDF/rdf:Description/dc:creator/rdf:Description")
        xp.assertNodeCount(1, "/rdf:RDF/rdf:Description/dc:creator/rdf:Description/dc:title")


    #@observer.log_function_events
    def test_remove_implied_type_property_from_root(self):
        r = get_root('''<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dc="http://purl.org/dc/elements/1.1/"
         xmlns:cc="http://creativecommons.org/ns#">
  <cc:Work rdf:about="">
    <dc:title>Test</dc:title>
  </cc:Work>
</rdf:RDF>
''')
        # cc:Agent is an invention in Inkscape - doesn't really exist in cc:
        
        xp = XPathAsserts(self, r.repr.element)

        # There's two resources: "" and cc:Work
        self.assertEqual(len(r), 2)

        res = r['']
        self.assertEqual(len(res), 2)

        # Get the implied rdf:type property
        rdftype = res[0]
        self.assertPredicate(rdftype, domrepr.RDF_NS + 'type',
                             model.ResourceNode, domrepr.ImpliedTypeProperty)

        type_node = rdftype.object

        title = res[1]
        
        with observer.AssertEvent(
            self, r,
            # Moving predicate to new rdf:Description element
            (model.PredicateRemoved, { 'predicate': title }),

            # Unlinking cc:Agent
            (model.PredicateRemoved, { 'predicate': rdftype }),
            (model.ResourceNodeRemoved, { 'node': res }),
            (model.ResourceNodeRemoved, { 'node': type_node}),

            # The re-added node and dc:title
            model.ResourceNodeAdded,
            model.PredicateAdded,
            ):
            rdftype.remove()
            
        # Check that model updated: cc:Work should now be
        # rdf:Description and the type node is gone
        self.assertEqual(len(r), 1)

        # Just dc:title now
        res = r['']
        self.assertEqual(len(res), 1)
        self.assertPredicate(res[0], 'http://purl.org/dc/elements/1.1/title',
                             model.LiteralNode, domrepr.LiteralProperty)

        # Check that XML updated
        xp.assertNodeCount(0, "/rdf:RDF/cc:Work")
        xp.assertNodeCount(1, "/rdf:RDF/rdf:Description")
        xp.assertNodeCount(1, "/rdf:RDF/rdf:Description/dc:title")
