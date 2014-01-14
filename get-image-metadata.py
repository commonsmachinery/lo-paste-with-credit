#! /usr/bin/python3
#
# get-image-metadata - Command line tool to extract image metadata inserted with the LO plugin
#
# Copyright 2014 Commons Machinery http://commonsmachinery.se/
#
# Authors: Peter Liljenberg <peter@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.

"""Usage: get-image-metadata.py [image-bookmark]

Without bookmark, list all images with bookmarks.
With bookmark, output metadata for that image.
"""

import sys
import uno
import unohelper

BOOKMARK_BASE_NAME = "$image-with-metadata$"

def main():
    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", localContext)

    # connect to the running office, start as:
    #     soffice "--accept=socket,host=localhost,port=2002;urp;" --writer
    ctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    smgr = ctx.ServiceManager
    
    desktop = smgr.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)
    
    model = desktop.getCurrentComponent()

    if len(sys.argv) == 1:
        list_images(model)
    else:
        get_image_metadata(ctx, model, sys.argv[1])
        

def list_images(model):
    names = model.getBookmarks().getElementNames()
    for n in names:
        if n.startswith(BOOKMARK_BASE_NAME):
            print(n)

def get_image_metadata(ctx, model, name):
    bookmark = model.getBookmarks().getByName(name)

    seen_subjects = {}
    repository = model.getRDFRepository()
    dump_statements(repository, bookmark, seen_subjects)

def dump_statements(repository, subject, seen_subjects):
    if subject.StringValue in seen_subjects:
        return

    seen_subjects[subject.StringValue] = 1
    
    statements = repository.getStatements(subject, None, None)
    while statements.hasMoreElements():
        s = statements.nextElement()
        dump_statement(s)
        if not hasattr(s.Object, 'Value'):
            # Recurse over non-literal
            dump_statements(repository, s.Object, seen_subjects)
            

def dump_statement(s):
    if hasattr(s.Object, 'Value'):
        obj = '"{0}"'.format(s.Object.Value)
    else:
        obj = '<{0}>'.format(s.Object.StringValue)

    if s.Graph:
        g = s.Graph.StringValue
    else:
        g = 'RDFa'

    print('<{0}> <{1}> {2} . # {3}'.format(
            s.Subject.StringValue,
            s.Predicate.StringValue,
            obj, g))
    
    

if __name__ == '__main__':
    main()
