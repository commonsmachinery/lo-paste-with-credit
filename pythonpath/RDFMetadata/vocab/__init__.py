# vocab - definitions and human-readable names for metadata terms
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Artem Popov <artfwo@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

import sys
import inspect

class Term(object):
    """
    Human-readable label and description for a metadata property.
    """
    def __init__(self, uri, label=None, desc=None, qname=None):
        self.uri = uri
        self.label = label
        self.desc = desc
        self.qname = qname

vocabularies = {}

from . import cc
from . import dc
from . import dcterms
from . import rdf
from . import xhtml

for module in [cc, dc, dcterms, rdf, xhtml]:
    vocabularies[module.NS_URI] = module

def get_terms(ns_uri):
    """
    Return a list of Term objects for a given namespace URI.

    If a special URI 'common_terms' is passed, return
    a list of frequently used metadata properties.
    """

    if ns_uri == 'common_terms':
        return get_common_terms()
    terms = []
    for name, value in inspect.getmembers(vocabularies[ns_uri], lambda v: isinstance(v, Term)):
        terms.append(value)
    return terms

def get_common_terms():
    """
    Return a list of Term objects for frequently used metadata properties.
    """

    return [
        dc.title,
        dc.creator,
        dc.date,
        cc.attributionName,
        cc.attributionURL,
        cc.license,
    ]

def get_term(ns_uri, localname):
    """
    Return a Term object given its namespace URI and local name.
    """

    ns_dic = vocabularies[ns_uri].__dict__
    if ns_dic.has_key(localname) and isinstance(ns_dic[localname], Term):
        return ns_dic[localname]
    else:
        raise LookupError("Term %s not found in vocabulary" % localname)

