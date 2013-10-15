# vocab - definitions and human-readable names for metadata terms
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Artem Popov <artfwo@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

import sys
from . import Term
from RDFMetadata import model

NS_URI = "http://www.w3.org/1999/xhtml/vocab#"
NS_PREFIX = "xhv"

license = Term(
    uri=NS_URI + "license",
    qname=model.QName(NS_URI, NS_PREFIX, "license"),
    label="License",
    desc="license refers to a resource that defines the associated license."
)
