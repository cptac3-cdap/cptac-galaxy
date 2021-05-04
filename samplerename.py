#!/bin/env python27

import sys, csv, re, shutil

replace = []
for r in csv.reader(open(sys.argv[1]),dialect='excel-tab'):
    if r[1].lower() == "withdrawn":
        replace.append((r[0],"Withdrawn:"+r[0]))
    elif len(r) == 2:
        replace.append((r[0],r[1]))
    else:
	raise RuntimeError("Incorrect number of columns in "+sys.argv[1])

for i in range(len(replace)):
    for j in range(len(replace)):
	if i == j:
	    continue
	assert replace[i][0] not in replace[j][0], "Bad sample substitution: %s contained in %s"%(replace[i][0],replace[j][0])

for f in sys.argv[2:]:
    shutil.move(f,f+".bak")
    wh = open(f,'wb')
    for l in open(f+".bak"):
	for i,(f,t) in enumerate(replace):
	    l = l.replace(f,"XXXXXX:%06d:XXXXXX"%(i,))
	for i,(f,t) in enumerate(replace):
	    l = l.replace("XXXXXX:%06d:XXXXXX"%(i,),t)
	wh.write(l)
    wh.close()
