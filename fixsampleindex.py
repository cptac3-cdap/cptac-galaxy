#!/bin/env python3.12
import sys, csv, re, shutil

samplefile = sys.argv[1]
regex = sys.argv[2]
try:
    regexgrp = sys.argv[3]
except IndexError:
    regexgrp = 1

reader = csv.DictReader(open(samplefile),dialect='excel-tab')
rows = list(reader)
headers =  list(reader.fieldnames)
newrows = []
for r in rows:
    m = re.search(regex,r['AnalyticalSample'])
    if not m:
        raise RuntimeError("Can't find analytical sample index in %s"%(r['AnalyticalSample'],))
    try:
        grp = int(m.group(regexgrp))
    except ValueError:
        grp = None
    if grp is None:
        raise RuntimeError("Can't make integer from %s: %s."%(r['AnalyticalSample'],m.group(regexgrp)))
    r['AnalyticalSampleIndex'] = str(grp)
    newrows.append(r)

shutil.move(samplefile, samplefile+'.orig') 
wh = open(samplefile,'w')
newheaders = list(headers)
if "AnalyticalSampleIndex" not in headers:
    newheaders.insert(2,"AnalyticalSampleIndex")
print("\t".join(newheaders),file=wh)
for r in newrows:
    print("\t".join(map(r.get,newheaders)),file=wh)
wh.close()
