# vocab - definitions and human-readable names for metadata terms
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Artem Popov <artfwo@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

# Note:
# this namespace only contains terms for properties.
# cc resource types are commented out (below)
# until we figure out how to properly plug them into
# the editor.

import sys
from . import Term
from RDFMetadata import model


NS_URI = "http://creativecommons.org/ns#"
NS_PREFIX = "cc"


attributionName = Term(
    uri=NS_URI + "attributionName",
    qname=model.QName(NS_URI, NS_PREFIX, "attributionName"),
    label="Attribution Name",
    desc=""
)

attributionURL = Term(
    uri=NS_URI + "attributionURL",
    qname=model.QName(NS_URI, NS_PREFIX, "attributionURL"),
    label="Attribution URL",
    desc=""
)

deprecatedOn = Term(
    uri=NS_URI + "deprecatedOn",
    qname=model.QName(NS_URI, NS_PREFIX, "deprecatedOn"),
    label="Deprecated On",
    desc=""
)

jurisdiction = Term(
    uri=NS_URI + "jurisdiction",
    qname=model.QName(NS_URI, NS_PREFIX, "jurisdiction"),
    label="Jurisdiction",
    desc=""
)

legalcode = Term(
    uri=NS_URI + "legalcode",
    qname=model.QName(NS_URI, NS_PREFIX, "legalcode"),
    label="Legal Code",
    desc=""
)

license = Term(
    uri=NS_URI + "license",
    qname=model.QName(NS_URI, NS_PREFIX, "license"),
    label="License",
    desc=""
)

morePermissions = Term(
    uri=NS_URI + "morePermissions",
    qname=model.QName(NS_URI, NS_PREFIX, "morePermissions"),
    label="More Permissions",
    desc=""
)

permits = Term(
    uri=NS_URI + "permits",
    qname=model.QName(NS_URI, NS_PREFIX, "permits"),
    label="Permits",
    desc=""
)

prohibits = Term(
    uri=NS_URI + "prohibits",
    qname=model.QName(NS_URI, NS_PREFIX, "prohibits"),
    label="Prohibits",
    desc=""
)

requires = Term(
    uri=NS_URI + "requires",
    qname=model.QName(NS_URI, NS_PREFIX, "requires"),
    label="Requires",
    desc=""
)

useGuidelines = Term(
    uri=NS_URI + "useGuidelines",
    qname=model.QName(NS_URI, NS_PREFIX, "useGuidelines"),
    label="Use Guidelines",
    desc=""
)

"""
Work = Term(
    uri=NS_URI + "Work",
    qname=model.QName(NS_URI, NS_PREFIX, "Work"),
    label="Work",
    desc="a potentially copyrightable work"
)

License = Term(
    uri=NS_URI + "License",
    qname=model.QName(NS_URI, NS_PREFIX, "License"),
    label="License",
    desc="a set of requests/permissions to users of a Work, e.g. a copyright license, the public domain, information for distributors"
)

Jurisdiction = Term(
    uri=NS_URI + "Jurisdiction",
    qname=model.QName(NS_URI, NS_PREFIX, "Jurisdiction"),
    label="Jurisdiction",
    desc="the legal jurisdiction of a license"
)

Permission = Term(
    uri=NS_URI + "Permission",
    qname=model.QName(NS_URI, NS_PREFIX, "Permission"),
    label="Permission",
    desc="an action that may or may not be allowed or desired"
)

Requirement = Term(
    uri=NS_URI + "Requirement",
    qname=model.QName(NS_URI, NS_PREFIX, "Requirement"),
    label="Requirement",
    desc="an action that may or may not be requested of you"
)

Prohibition = Term(
    uri=NS_URI + "Prohibition",
    qname=model.QName(NS_URI, NS_PREFIX, "Prohibition"),
    label="Prohibition",
    desc="something you may be asked not to do"
)

Reproduction = Term(
    uri=NS_URI + "Reproduction",
    qname=model.QName(NS_URI, NS_PREFIX, "Reproduction"),
    label="Reproduction",
    desc="making multiple copies"
)

Distribution = Term(
    uri=NS_URI + "Distribution",
    qname=model.QName(NS_URI, NS_PREFIX, "Distribution"),
    label="Distribution",
    desc="distribution, public display, and publicly performance"
)

DerivativeWorks = Term(
    uri=NS_URI + "DerivativeWorks",
    qname=model.QName(NS_URI, NS_PREFIX, "DerivativeWorks"),
    label="Derivative Works",
    desc="distribution of derivative works"
)

Sharing = Term(
    uri=NS_URI + "Sharing",
    qname=model.QName(NS_URI, NS_PREFIX, "Sharing"),
    label="Sharing",
    desc="permits commercial derivatives, but only non-commercial distribution"
)

Notice = Term(
    uri=NS_URI + "Notice",
    qname=model.QName(NS_URI, NS_PREFIX, "Notice"),
    label="Notice",
    desc="copyright and license notices be kept intact"
)

Attribution = Term(
    uri=NS_URI + "Attribution",
    qname=model.QName(NS_URI, NS_PREFIX, "Attribution"),
    label="Attribution",
    desc="credit be given to copyright holder and/or author"
)

ShareAlike = Term(
    uri=NS_URI + "ShareAlike",
    qname=model.QName(NS_URI, NS_PREFIX, "ShareAlike"),
    label="Share Alike",
    desc="derivative works be licensed under the same terms or compatible terms as the original work"
)

SourceCode = Term(
    uri=NS_URI + "SourceCode",
    qname=model.QName(NS_URI, NS_PREFIX, "SourceCode"),
    label="Source Code",
    desc="source code (the preferred form for making modifications) must be provided when exercising some rights granted by the license."
)

Copyleft = Term(
    uri=NS_URI + "Copyleft",
    qname=model.QName(NS_URI, NS_PREFIX, "Copyleft"),
    label="Copyleft",
    desc="derivative and combined works must be licensed under specified terms, similar to those on the original work"
)

LesserCopyleft = Term(
    uri=NS_URI + "LesserCopyleft",
    qname=model.QName(NS_URI, NS_PREFIX, "LesserCopyleft"),
    label="Lesser Copyleft",
    desc="derivative works must be licensed under specified terms, with at least the same conditions as the original work; combinations with the work may be licensed under different terms"
)

CommercialUse = Term(
    uri=NS_URI + "CommercialUse",
    qname=model.QName(NS_URI, NS_PREFIX, "CommercialUse"),
    label="Commercial Use",
    desc="exercising rights for commercial purposes"
)

HighIncomeNationUse = Term(
    uri=NS_URI + "HighIncomeNationUse",
    qname=model.QName(NS_URI, NS_PREFIX, "HighIncomeNationUse"),
    label="High Income Nation Use",
    desc="use in a non-developing country"
)
"""
