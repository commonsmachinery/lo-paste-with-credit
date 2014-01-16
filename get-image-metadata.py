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
With bookmark, output metadata for that image as RDF_XML
"""

import sys
import uuid

import uno
import unohelper

from com.sun.star.rdf.FileFormat import RDF_XML
from com.sun.star.io import XOutputStream

BOOKMARK_BASE_NAME = "$metadata-tag-do-not-edit$"

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

    repository = model.getRDFRepository()

    ss = StringOutputStream()
    
    seen_subjects = {}

    # Copy statements to a temporary graph
    graph_uri = uri(ctx, 'urn:' + str(uuid.uuid4()) + '#temp')
    target_graph = repository.createGraph(graph_uri)
    try:
        copy_statements(repository, bookmark, seen_subjects, target_graph)
        repository.exportGraph(RDF_XML, ss, graph_uri, model)
    finally:
        repository.destroyGraph(graph_uri)

    print(str(ss))
    

def copy_statements(repository, subject, seen_subjects, graph):
    if subject.StringValue in seen_subjects:
        return

    seen_subjects[subject.StringValue] = 1
    
    statements = repository.getStatements(subject, None, None)
    while statements.hasMoreElements():
        s = statements.nextElement()

        # Only copy if not a duplicate
        if not graph.getStatements(s.Subject, s.Predicate, s.Object).hasMoreElements():
            graph.addStatement(s.Subject, s.Predicate, s.Object)
        
            if not hasattr(s.Object, 'Value'):
                # Recurse over non-literal
                copy_statements(repository, s.Object, seen_subjects, graph)
            

def uri(ctx, string):
    return ctx.ServiceManager.createInstanceWithArguments(
        "com.sun.star.rdf.URI", (string, ))


class StringOutputStream(unohelper.Base, XOutputStream):
    def __init__(self):
        self.s = uno.ByteSequence('')

    def writeBytes(self, data):
        self.s = self.s + data

    def flush(self):
        pass

    def closeOutput(self):
        pass

    def __str__(self):
        return self.s.value.decode('utf-8')
    


if __name__ == '__main__':
    main()
