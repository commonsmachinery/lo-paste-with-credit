lo-paste-with-credit
====================

LibreOffice extension for pasting images with automatic attribution.

This extension requires CopyRDF browser addon to work properly. Get it here:
https://github.com/commonsmachinery/copyrdf-addon

Installation
------------

1. Download `paste_with_credit.oxt`;
1. In LibreOffice go to "Tools->Extension Manager...";
2. Click "Add..."  and choose `paste-with-credit.oxt`.

Usage
-----

To paste an image and automatically add credit data:

1. Copy an image with metadata from Firefox.
2. Paste via "Edit->Paste with credit".

To copy image with credit metadata back to clipboard:

1. Right-click the image.
2. Choose "Copy with metadata"

To generate a credits block in Impress:

1. Paste one or more images using "Edit->Paste with credit"
2. Choose "Insert->Credits" from the main menu.

License
-------

Copyright 2013 Commons Machinery http://commonsmachinery.se/

Author(s): Artem Popov <artfwo@commonsmachinery.se>,
           Peter Liljenberg <peter@commonsmachinery.se>

Distributed under an GPLv2 license, please see the LICENSE file for details.

Bundled libraries
-----------------

The extension package (`paste_with_credit.oxt`) includes the following libraries:

**libcredit**

    https://github.com/commonsmachinery/libcredit
    Copyright 2013 Commons Machinery http://commonsmachinery.se/
    License: GPL license, version 2

**RDFLib**

    https://github.com/RDFLib/rdflib
    Copyright (c) 2002-2012, RDFLib Team
    License: BSD license, 3-clause version

**isodate**

    https://github.com/gweis/isodate
    Copyright 2009, Gerhard Weis
    License: BSD license, 3-clause version

**pyparsing**

    http://sourceforge.net/projects/pyparsing/
    Copyright (c) 2003-2013  Paul T. McGuire
    License: MIT license
