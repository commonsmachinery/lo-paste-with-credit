# test_namespaces - Test namespace handling when parsing RDF/XML
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Peter Liljenberg <peter@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

import sys
import unittest
from xml.dom import minidom

# https://pypi.python.org/pypi/py-dom-xpath
import xpath

from .. import parser


class TestNamespaceParsing(unittest.TestCase):
    def setUp(self):
        self.doc = minidom.parseString('''<?xml version="1.0"?>
<root xmlns="urn:root#"
      xmlns:dc="urn:dc#"
      xmlns:rdf="urn:not-rdf-top#">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="">
    <dc:creator>
      <rdf:struct xmlns:rdf="urn:not-rdf#">
        <rdf:foo>Test</rdf:foo>
      </rdf:struct>
    </dc:creator>
  </rdf:Description>
</rdf:RDF>
</root>''')

        rdf = self.doc.getElementsByTagName('rdf:RDF')[0]
        self.root = parser.parse_RDFXML(doc = self.doc, root_element = rdf)


    def tearDown(self):
        self.root = None
        
    def test_root_ns(self):
        # Check that the root repr has default and dc

        ns = self.root.repr.namespaces

        self.assertEqual(ns.get_prefix("urn:root#", "root"), None)
        self.assertEqual(ns.get_prefix("urn:dc#", "dc2"), "dc")
        
    def test_add_to_root_ns(self):
        # Test adding a new namespace directly to root

        ns = self.root.repr.namespaces

        self.assertEqual(ns.get_prefix("urn:new#", "new"), "new")
        self.assertEqual("urn:new#", ns.element.getAttribute("xmlns:new"))

    def test_add_conflict_to_root_ns(self):
        # Test adding a new namespace directly to root with a prefix in use

        ns = self.root.repr.namespaces

        self.assertEqual(ns.get_prefix("urn:new#", "dc"), "dc2")
        self.assertEqual("urn:new#", ns.element.getAttribute("xmlns:dc2"))
        

    def test_recursive1_lookup(self):
        # Test that we can find prefixes even a bit down
        res = self.root[""]
        ns = res.reprs[0].repr.namespaces
        
        self.assertEqual(ns.get_prefix("urn:root#", "root"), None)
        self.assertEqual(ns.get_prefix("urn:dc#", "dcx"), "dc")
        self.assertEqual(ns.get_prefix("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdfx"), "rdf")


    def test_recursive2_lookup(self):
        # Test that we can find prefixes even way down
        pred = self.root[""][0].object[1]
        ns = pred.repr.repr.namespaces
        
        self.assertEqual(ns.get_prefix("urn:root#", "root"), None)
        self.assertEqual(ns.get_prefix("urn:dc#", "dc2"), "dc")

    def test_local_scope(self):
        # Check that in "rdf:foo" rdf: means something else

        pred = self.root[""][0].object[1]
        ns = pred.repr.repr.namespaces

        self.assertEqual(ns.get_prefix("urn:not-rdf#", "rdfx"), "rdf")


    def test_bring_into_scope(self):
        # Test that the normal rdf: namespace is brought back in scope when needed

        pred = self.root[""][0].object[1]
        ns = pred.repr.repr.namespaces

        self.assertEqual(ns.get_prefix("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdf"), "rdf2")

        # The prefix will be redefined in the dc:creator object
        obj = self.root[""][0].object
        ns2 = obj.reprs[0].repr.namespaces
        self.assertEqual("http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                         ns2.element.getAttribute("xmlns:rdf2"))
        
