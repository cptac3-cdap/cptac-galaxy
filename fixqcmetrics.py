#!/bin/env python

import csv, re, sys, shutil
from optparse import OptionParser
from collections import defaultdict

p = OptionParser()
p.add_option('--analsamp',type='string',dest="asregex",default=None,
             help="Analytical sample regular expression. Required.")
p.add_option('--analsampgrp',type='int',dest="asregexgrp",default=1,
             help="Analytical sample regular expression group. Default: 1.")
p.add_option('--analsampsort',type='string',dest="assortregex",default=None,
             help="Analytical sample sorting value regular expression. Required.")
p.add_option('--analsampsortgrp',type='string',dest="assortregexgrp",default=1,
             help="Analytical sample sorting value regular expression group. Default: 1.")
p.add_option('--analsampexpr',type='string',dest='asexpr',default=None,
	     help='Python expression to evaluate on extracted analytical sample')
p.add_option('--fraction',type='string',dest="fnregex",default=None,
             help="Fraction number regular expression. Required.")
p.add_option('--fractiongrp',type='int',dest="fnregexgrp",default=1,
             help="Fraction number regular expression group. Default: 1.")
p.add_option('--fractionexpr',type='string',dest='fnexpr',default=None,
	     help='Python expression to evaluate on extracted fraction number')
p.add_option('-i',action='store_true',dest="inplace",default=False,
	     help="In-place: Overwrite input file with output. Default: False")
opts,args = p.parse_args()

if not opts.asregex:
    p.error("Analytical sample regular expression required.")
else:
    asregex = re.compile(opts.asregex)
if not opts.fnregex:
    p.error("Fraction number regular expression required.")
else:
    fnregex = re.compile(opts.fnregex)
if opts.assortregex:
    assortregex = re.compile(opts.assortregex)
def tofracnum(value):
    try:
	return int(value)
    except ValueError:
	pass
    return value

def toind(value):
    try:
	return int(value),""
    except ValueError:
        pass
    return 1000000,value

asfreq = defaultdict(int)
frfreq = defaultdict(int)
assortkey = {}
frsortkey = {}
rows = csv.DictReader(open(args[0]),dialect='excel-tab')
outrows = []
for r in rows:
    # spectrumBasename        analyticalBasename      fractionNum
    sb = r['spectrumBasename']
    m = asregex.search(sb)
    if not m:
        p.error("Analytical sample regular expression doesn't match: %s"%(sb,))
    asamp = m.group(opts.asregexgrp)
    r['analyticalBasenameSortKey'] = toind(asamp)
    if opts.assortregex:
	m = assortregex.search(sb)
	if not m:
	    p.error("Analytical sample sort key regular expression doesn't match: %s"%(sb,))
	r['analyticalBasenameSortKey'] = toind(m.group(opts.assortregexgrp))
    if opts.asexpr != None:
	asamp = str(eval(opts.asexpr,globals(),dict(x=asamp)))
    r['analyticalBasename'] = asamp
    m = fnregex.search(sb)
    if not m:
	p.error("Fraction number regular expression doesn't match: %s"%(sb,))
    fn = m.group(opts.fnregexgrp)
    if opts.fnexpr != None:
	fn = str(eval(opts.fnexpr,globals(),dict(x=tofracnum(fn))))
    r['fractionNum'] = fn
    r['fractionNumSortKey'] = toind(fn)

    assortkey[r['analyticalBasename']] = r['analyticalBasenameSortKey']
    asfreq[r['analyticalBasename']] += 1
    frsortkey[r['fractionNum']] = r['fractionNumSortKey']
    frfreq[r['fractionNum']] += 1

    outrows.append(dict(r.items()))

outrows.sort(key=lambda r: (r['analyticalBasenameSortKey'],r['fractionNumSortKey']))

if opts.inplace:
  shutil.move(args[0], args[0]+'.bak')
  wh = open(args[0],'w')
else:
  wh = sys.stdout
dw = csv.DictWriter(wh,fieldnames=rows.fieldnames,dialect='excel-tab',extrasaction='ignore')
dw.writerow(dict(zip(rows.fieldnames,rows.fieldnames)))
dw.writerows(outrows)
if opts.inplace:
  wh.close()
else:
  sys.stdout.flush()

print >>sys.stderr
print >>sys.stderr, "Analytical Samples:"
for as in sorted(asfreq,key=assortkey.get):
    print >>sys.stderr, as,asfreq[as]
print >>sys.stderr

print >>sys.stderr, "Fractions:"
for fr in sorted(frfreq,key=frsortkey.get):
    print >>sys.stderr, fr, frfreq[fr]
