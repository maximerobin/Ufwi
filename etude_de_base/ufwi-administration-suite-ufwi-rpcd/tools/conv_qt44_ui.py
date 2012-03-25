#!/usr/bin/env python
from ufwi_rpcd.common.xml_etree import etree
from sys import argv, stderr, exit

def main():
    if len(argv) != 2:
        print >>stderr, "usage: %s filename.ui" % argv[0]
        exit(1)
    filename = argv[1]
    doc = etree.parse(filename)
    replaced = 0
    for iconset in doc.getroot().getiterator('iconset'):
        normaloff = iconset.find('normaloff')
        if normaloff is None:
            continue
        iconset.text = normaloff.text.strip()
        iconset.remove(normaloff)
        iconset.tail = u''
        replaced += 1
    if not replaced:
        print "No <iconset> modified: file format is already Qt 4.3?"
        exit(1)

    out = open(filename, 'w')
    doc.write(out)
    out.close()
    print "Conversion done: %s (%s <iconset> modified)" % (filename, replaced)
    exit(0)

if __name__ == "__main__":
    main()

