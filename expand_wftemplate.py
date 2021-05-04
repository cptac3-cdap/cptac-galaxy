#!/bin/env python27
import sys, os, json, csv, re
from optparse import OptionParser

species_data = """
key             genemap
Human           prhuman2gene.csv
Mouse           prmouse2gene.csv
Rat             prrat2gene.csv
Human-Mouse     prhumanmouse2gene.csv
"""
species = dict()
headers = None
for i,l in enumerate(species_data.splitlines()):
    if not l.strip():
        continue
    sl = list(map(str.strip,re.split(r'\t+',l.strip())))
    if headers == None:
        headers = sl
        continue
    r = dict(list(zip(headers,sl)))
    species[r['key']] = r

labels_data = """
key
TMT10
TMT11
TMT6
iTRAQ
Label-Free
"""
labels = dict()
for i,l in enumerate(labels_data.splitlines()):
    if not l.strip():
        continue
    sl = list(map(str.strip,re.split(r'\t+',l.strip())))
    if i == 0:
        headers = sl
        continue
    r = dict(list(zip(headers,sl)))
    labels[r['key']] = r

parser = OptionParser()
parser.add_option("--template", type="string", dest="template", default=None,
                  metavar="TEMPLATE",
                  help="Template file. Required.")
parser.add_option("--species", type="choice", dest="species", default=None,
                  metavar="SPECIES", choices=sorted(species),
                  help="Species. One of %s. Required."%(", ".join(sorted(species))))
parser.add_option("--labels", type="choice", dest="labels", default=None,
                  metavar="LABELS", choices=sorted(labels),
                  help="Labels. One of %s. Required."%(", ".join(sorted(labels))))
parser.add_option("--force", action="store_true", dest="force", default=False,
                  help="Overwrite existing workflow. Default: False.")

opts,args = parser.parse_args()
assert opts.template
assert os.path.exists(opts.template)
assert opts.species
assert opts.labels

contents = open(opts.template).read()
contents = contents.replace('XXX-SPECIES-XXX',opts.species)
contents = contents.replace('XXX-LABELS-XXX',opts.labels)
contents = contents.replace('XXX-GENEMAP-XXX',species[opts.species]['genemap'])
wf = json.loads(contents)
wfname = wf['name']
wffilename = 'Galaxy-Workflow-%s.ga'%(wfname.replace(' ','_').replace('+','_'),)

if not opts.force and os.path.exists(wffilename):
    raise RuntimeError("Won't overwrite %s"%(wffilename,))

wh = open(wffilename,'w')
wh.write(contents)
wh.close()
