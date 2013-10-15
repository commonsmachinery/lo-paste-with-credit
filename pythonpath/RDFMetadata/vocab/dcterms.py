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

NS_URI = "http://purl.org/dc/terms/"
NS_PREFIX = "dcterms"

abstract = Term(
    uri=NS_URI + "abstract",
    qname=model.QName(NS_URI, NS_PREFIX, "abstract"),
    label="Abstract",
    desc="A summary of the resource."
)

accessRights = Term(
    uri=NS_URI + "accessRights",
    qname=model.QName(NS_URI, NS_PREFIX, "accessRights"),
    label="Access Rights",
    desc="Information about who can access the resource or an indication of its security status."
)

accrualMethod = Term(
    uri=NS_URI + "accrualMethod",
    qname=model.QName(NS_URI, NS_PREFIX, "accrualMethod"),
    label="Accrual Method",
    desc="The method by which items are added to a collection."
)

accrualPeriodicity = Term(
    uri=NS_URI + "accrualPeriodicity",
    qname=model.QName(NS_URI, NS_PREFIX, "accrualPeriodicity"),
    label="Accrual Periodicity",
    desc="The frequency with which items are added to a collection."
)

accrualPolicy = Term(
    uri=NS_URI + "accrualPolicy",
    qname=model.QName(NS_URI, NS_PREFIX, "accrualPolicy"),
    label="Accrual Policy",
    desc="The policy governing the addition of items to a collection."
)

alternative = Term(
    uri=NS_URI + "alternative",
    qname=model.QName(NS_URI, NS_PREFIX, "alternative"),
    label="Alternative Title",
    desc="An alternative name for the resource."
)

audience = Term(
    uri=NS_URI + "audience",
    qname=model.QName(NS_URI, NS_PREFIX, "audience"),
    label="Audience",
    desc="A class of entity for whom the resource is intended or useful."
)

available = Term(
    uri=NS_URI + "available",
    qname=model.QName(NS_URI, NS_PREFIX, "available"),
    label="Date Available",
    desc="Date (often a range) that the resource became or will become available."
)

bibliographicCitation = Term(
    uri=NS_URI + "bibliographicCitation",
    qname=model.QName(NS_URI, NS_PREFIX, "bibliographicCitation"),
    label="Bibliographic Citation",
    desc="A bibliographic reference for the resource."
)

conformsTo = Term(
    uri=NS_URI + "conformsTo",
    qname=model.QName(NS_URI, NS_PREFIX, "conformsTo"),
    label="Conforms To",
    desc="An established standard to which the described resource conforms."
)

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

created = Term(
    uri=NS_URI + "created",
    qname=model.QName(NS_URI, NS_PREFIX, "created"),
    label="Date Created",
    desc="Date of creation of the resource."
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

dateAccepted = Term(
    uri=NS_URI + "dateAccepted",
    qname=model.QName(NS_URI, NS_PREFIX, "dateAccepted"),
    label="Date Accepted",
    desc="Date of acceptance of the resource."
)

dateCopyrighted = Term(
    uri=NS_URI + "dateCopyrighted",
    qname=model.QName(NS_URI, NS_PREFIX, "dateCopyrighted"),
    label="Date Copyrighted",
    desc="Date of copyright."
)

dateSubmitted = Term(
    uri=NS_URI + "dateSubmitted",
    qname=model.QName(NS_URI, NS_PREFIX, "dateSubmitted"),
    label="Date Submitted",
    desc="Date of submission of the resource."
)

description = Term(
    uri=NS_URI + "description",
    qname=model.QName(NS_URI, NS_PREFIX, "description"),
    label="Description",
    desc="An account of the resource."
)

educationLevel = Term(
    uri=NS_URI + "educationLevel",
    qname=model.QName(NS_URI, NS_PREFIX, "educationLevel"),
    label="Audience Education Level",
    desc="A class of entity, defined in terms of progression through an educational or training context, for which the described resource is intended."
)

extent = Term(
    uri=NS_URI + "extent",
    qname=model.QName(NS_URI, NS_PREFIX, "extent"),
    label="Extent",
    desc="The size or duration of the resource."
)

format = Term(
    uri=NS_URI + "format",
    qname=model.QName(NS_URI, NS_PREFIX, "format"),
    label="Format",
    desc="The file format, physical medium, or dimensions of the resource."
)

hasFormat = Term(
    uri=NS_URI + "hasFormat",
    qname=model.QName(NS_URI, NS_PREFIX, "hasFormat"),
    label="Has Format",
    desc="A related resource that is substantially the same as the pre-existing described resource, but in another format."
)

hasPart = Term(
    uri=NS_URI + "hasPart",
    qname=model.QName(NS_URI, NS_PREFIX, "hasPart"),
    label="Has Part",
    desc="A related resource that is included either physically or logically in the described resource."
)

hasVersion = Term(
    uri=NS_URI + "hasVersion",
    qname=model.QName(NS_URI, NS_PREFIX, "hasVersion"),
    label="Has Version",
    desc="A related resource that is a version, edition, or adaptation of the described resource."
)

identifier = Term(
    uri=NS_URI + "identifier",
    qname=model.QName(NS_URI, NS_PREFIX, "identifier"),
    label="Identifier",
    desc="An unambiguous reference to the resource within a given context."
)

instructionalMethod = Term(
    uri=NS_URI + "instructionalMethod",
    qname=model.QName(NS_URI, NS_PREFIX, "instructionalMethod"),
    label="Instructional Method",
    desc="A process, used to engender knowledge, attitudes and skills, that the described resource is designed to support."
)

isFormatOf = Term(
    uri=NS_URI + "isFormatOf",
    qname=model.QName(NS_URI, NS_PREFIX, "isFormatOf"),
    label="Is Format Of",
    desc="A related resource that is substantially the same as the described resource, but in another format."
)

isPartOf = Term(
    uri=NS_URI + "isPartOf",
    qname=model.QName(NS_URI, NS_PREFIX, "isPartOf"),
    label="Is Part Of",
    desc="A related resource in which the described resource is physically or logically included."
)

isReferencedBy = Term(
    uri=NS_URI + "isReferencedBy",
    qname=model.QName(NS_URI, NS_PREFIX, "isReferencedBy"),
    label="Is Referenced By",
    desc="A related resource that references, cites, or otherwise points to the described resource."
)

isReplacedBy = Term(
    uri=NS_URI + "isReplacedBy",
    qname=model.QName(NS_URI, NS_PREFIX, "isReplacedBy"),
    label="Is Replaced By",
    desc="A related resource that supplants, displaces, or supersedes the described resource."
)

isRequiredBy = Term(
    uri=NS_URI + "isRequiredBy",
    qname=model.QName(NS_URI, NS_PREFIX, "isRequiredBy"),
    label="Is Required By",
    desc="A related resource that requires the described resource to support its function, delivery, or coherence."
)

issued = Term(
    uri=NS_URI + "issued",
    qname=model.QName(NS_URI, NS_PREFIX, "issued"),
    label="Date Issued",
    desc="Date of formal issuance (e.g., publication) of the resource."
)

isVersionOf = Term(
    uri=NS_URI + "isVersionOf",
    qname=model.QName(NS_URI, NS_PREFIX, "isVersionOf"),
    label="Is Version Of",
    desc="A related resource of which the described resource is a version, edition, or adaptation."
)

language = Term(
    uri=NS_URI + "language",
    qname=model.QName(NS_URI, NS_PREFIX, "language"),
    label="Language",
    desc="A language of the resource."
)

license = Term(
    uri=NS_URI + "license",
    qname=model.QName(NS_URI, NS_PREFIX, "license"),
    label="License",
    desc="A legal document giving official permission to do something with the resource."
)

mediator = Term(
    uri=NS_URI + "mediator",
    qname=model.QName(NS_URI, NS_PREFIX, "mediator"),
    label="Mediator",
    desc="An entity that mediates access to the resource and for whom the resource is intended or useful."
)

medium = Term(
    uri=NS_URI + "medium",
    qname=model.QName(NS_URI, NS_PREFIX, "medium"),
    label="Medium",
    desc="The material or physical carrier of the resource."
)

modified = Term(
    uri=NS_URI + "modified",
    qname=model.QName(NS_URI, NS_PREFIX, "modified"),
    label="Date Modified",
    desc="Date on which the resource was changed."
)

provenance = Term(
    uri=NS_URI + "provenance",
    qname=model.QName(NS_URI, NS_PREFIX, "provenance"),
    label="Provenance",
    desc="A statement of any changes in ownership and custody of the resource since its creation that are significant for its authenticity, integrity, and interpretation."
)

publisher = Term(
    uri=NS_URI + "publisher",
    qname=model.QName(NS_URI, NS_PREFIX, "publisher"),
    label="Publisher",
    desc="An entity responsible for making the resource available."
)

references = Term(
    uri=NS_URI + "references",
    qname=model.QName(NS_URI, NS_PREFIX, "references"),
    label="References",
    desc="A related resource that is referenced, cited, or otherwise pointed to by the described resource."
)

relation = Term(
    uri=NS_URI + "relation",
    qname=model.QName(NS_URI, NS_PREFIX, "relation"),
    label="Relation",
    desc="A related resource."
)

replaces = Term(
    uri=NS_URI + "replaces",
    qname=model.QName(NS_URI, NS_PREFIX, "replaces"),
    label="Replaces",
    desc="A related resource that is supplanted, displaced, or superseded by the described resource."
)

requires = Term(
    uri=NS_URI + "requires",
    qname=model.QName(NS_URI, NS_PREFIX, "requires"),
    label="Requires",
    desc="A related resource that is required by the described resource to support its function, delivery, or coherence."
)

rights = Term(
    uri=NS_URI + "rights",
    qname=model.QName(NS_URI, NS_PREFIX, "rights"),
    label="Rights",
    desc="Information about rights held in and over the resource."
)

rightsHolder = Term(
    uri=NS_URI + "rightsHolder",
    qname=model.QName(NS_URI, NS_PREFIX, "rightsHolder"),
    label="Rights Holder",
    desc="A person or organization owning or managing rights over the resource."
)

source = Term(
    uri=NS_URI + "source",
    qname=model.QName(NS_URI, NS_PREFIX, "source"),
    label="Source",
    desc="A related resource from which the described resource is derived."
)

spatial = Term(
    uri=NS_URI + "spatial",
    qname=model.QName(NS_URI, NS_PREFIX, "spatial"),
    label="Spatial Coverage",
    desc="Spatial characteristics of the resource."
)

subject = Term(
    uri=NS_URI + "subject",
    qname=model.QName(NS_URI, NS_PREFIX, "subject"),
    label="Subject",
    desc="The topic of the resource."
)

tableOfContents = Term(
    uri=NS_URI + "tableOfContents",
    qname=model.QName(NS_URI, NS_PREFIX, "tableOfContents"),
    label="Table Of Contents",
    desc="A list of subunits of the resource."
)

temporal = Term(
    uri=NS_URI + "temporal",
    qname=model.QName(NS_URI, NS_PREFIX, "temporal"),
    label="Temporal Coverage",
    desc="Temporal characteristics of the resource."
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

valid = Term(
    uri=NS_URI + "valid",
    qname=model.QName(NS_URI, NS_PREFIX, "valid"),
    label="Date Valid",
    desc="Date (often a range) of validity of a resource."
)
