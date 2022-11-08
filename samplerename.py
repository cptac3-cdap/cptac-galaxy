#!/bin/env python3

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

for fn in sys.argv[2:]:
    shutil.move(fn,fn+".bak")
    wh = open(fn,'w')
    for l in open(fn+".bak"):
        for i,(f,t) in enumerate(replace):
            l = re.sub(r'\b%s\b'%(f,),"XXXXXX:%06d:XXXXXX"%(i,),l)
        for i,(f,t) in enumerate(replace):
            l = l.replace("XXXXXX:%06d:XXXXXX"%(i,),t)
        wh.write(l)
    wh.close()
