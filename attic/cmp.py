#!/bin/env python27
import csv, sys

# DeNovoScore
# PhosphoRSPeptide
ignore = set(filter(None,"""
Evalue
Qvalue
PepQvalue
Protein
""".split()))
ignore = []

def sortkey(r):
    return int(r['ScanNum']),r['PeptideSequence']

reader1 = iter(sorted(csv.DictReader(open(sys.argv[1]),dialect='excel-tab'),key=sortkey))
reader2 = iter(sorted(csv.DictReader(open(sys.argv[2]),dialect='excel-tab'),key=sortkey))
r1 = reader1.next()
r1count = 1
r2 = reader2.next()
r2count = 1
r12count = 0
while True:
    try:
        while sortkey(r1) != sortkey(r2):
	    if sortkey(r1) < sortkey(r2):
	        r1 = reader1.next()
		r1count += 1
	    elif sortkey(r1) > sortkey(r2):
	        r2 = reader2.next()
		r2count += 1
        assert sortkey(r1) == sortkey(r2)
	r12count += 1
        commonkeys = set(r1.keys())
	allkeys = commonkeys.union(r2.keys())	
	allkeys = filter(None,allkeys)
        commonkeys = commonkeys.intersection(r2.keys())
	commonkeys = filter(None,commonkeys)
        equalkeys = set()
        ignorekeys = set()
        uniqkeys = set()
        print "Scan:",r1['ScanNum'],r1['PeptideSequence'],r12count,r1count-r12count,r2count-r12count
        for k in sorted(allkeys):
	    if k in ignore:
		ignorekeys.add(k)
		continue
	    if k not in commonkeys:
		uniqkeys.add(k)
		continue
	    if r1[k] != r2[k]:
		try:
		    if abs(float(r1[k])) > 0 and abs(float(r1[k]) - float(r2[k]))/abs(float(r1[k])) < 0.01:
	                print " ~~~ ",k,r1[k] if r1[k] != "" else "-", "!=",  r2[k] if r2[k] != "" else "-"
		    elif abs(float(r2[k])) > 0 and abs(float(r1[k]) - float(r2[k]))/abs(float(r2[k])) < 0.01:
	                print " ~~~ ",k,r1[k] if r1[k] != "" else "-", "!=",  r2[k] if r2[k] != "" else "-"
		    else:
	                print " !!! ",k,r1[k] if r1[k] != "" else "-", "!=",  r2[k] if r2[k] != "" else "-"
		except ValueError:
	            print " !!! ",k,r1[k] if r1[k] != "" else "-", "!=",  r2[k] if r2[k] != "" else "-"
	    else:
		equalkeys.add(k)
        for k in sorted(equalkeys):
	    print " EEE ",k
        for k in sorted(uniqkeys):
	    print " UUU ",k
        for k in sorted(ignorekeys):
	    print " III ",k
        r1 =  reader1.next()
	r1count += 1
    except StopIteration:
	break
