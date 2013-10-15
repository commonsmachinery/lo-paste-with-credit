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

NS_URI = "http://purl.org/dc/elements/1.1/"
NS_PREFIX = "dc"

contributor = Term(
    uri=NS_URI + "contributor",
    qname=model.QName(NS_URI, NS_PREFIX, "contributor"),
    label="Contributor",
    desc="An entity responsible for making contributions to the resource."
)

coverage = Term(
    uri=NS_URI + "coverage",
    qname=model.QName(NS_URI, NS_PREFIX, "coverage"),
    label="Coverage",
    desc="The spatial or temporal topic of the resource, the spatial applicability of the resource, or the jurisdiction under which the resource is relevant."
)

creator = Term(
    uri=NS_URI + "creator",
    qname=model.QName(NS_URI, NS_PREFIX, "creator"),
    label="Creator",
    desc="An entity primarily responsible for making the resource."
)

date = Term(
    uri=NS_URI + "date",
    qname=model.QName(NS_URI, NS_PREFIX, "date"),
    label="Date",
    desc="A point or period of time associated with an event in the lifecycle of the resource."
)

description = Term(
    uri=NS_URI + "description",
    qname=model.QName(NS_URI, NS_PREFIX, "description"),
    label="Description",
    desc="An account of the resource."
)

format = Term(
    uri=NS_URI + "format",
    qname=model.QName(NS_URI, NS_PREFIX, "format"),
    label="Format",
    desc="The file format, physical medium, or dimensions of the resource."
)

identifier = Term(
    uri=NS_URI + "identifier",
    qname=model.QName(NS_URI, NS_PREFIX, "identifier"),
    label="Identifier",
    desc="An unambiguous reference to the resource within a given context."
)

language = Term(
    uri=NS_URI + "language",
    qname=model.QName(NS_URI, NS_PREFIX, "language"),
    label="Language",
    desc="A language of the resource."
)

publisher = Term(
    uri=NS_URI + "publisher",
    qname=model.QName(NS_URI, NS_PREFIX, "publisher"),
    label="Publisher",
    desc="An entity responsible for making the resource available."
)

relation = Term(
    uri=NS_URI + "relation",
    qname=model.QName(NS_URI, NS_PREFIX, "relation"),
    label="Relation",
    desc="A related resource."
)

rights = Term(
    uri=NS_URI + "rights",
    qname=model.QName(NS_URI, NS_PREFIX, "rights"),
    label="Rights",
    desc="Information about rights held in and over the resource."
)

source = Term(
    uri=NS_URI + "source",
    qname=model.QName(NS_URI, NS_PREFIX, "source"),
    label="Source",
    desc="A related resource from which the described resource is derived."
)

subject = Term(
    uri=NS_URI + "subject",
    qname=model.QName(NS_URI, NS_PREFIX, "subject"),
    label="Subject",
    desc="The topic of the resource."
)

title = Term(
    uri=NS_URI + "title",
    qname=model.QName(NS_URI, NS_PREFIX, "title"),
    label="Title",
    desc="A name given to the resource."
)

type = Term(
    uri=NS_URI + "type",
    qname=model.QName(NS_URI, NS_PREFIX, "type"),
    label="Type",
    desc="The nature or genre of the resource."
)
