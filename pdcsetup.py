#!/bin/env python


import sys, os, os.path, shutil, re, uuid, traceback

from requests.exceptions import ConnectionError

from optparse import OptionParser, OptionGroup
parser = OptionParser()

parser.add_option("--study",type="string",dest="studyid",default=None,help="Study. For example: c935c587-0cd1-11e9-a064-0a9c39d33490 or S043-1.")
parser.add_option("--jobid",type="string",dest="jobid",default=None,help="Job id. Optional.")
parser.add_option("--pdcapi",type="choice",dest="pdcapi",default="PROD",choices=["DEV","STAGE","PROD"],
                  help="PDC API server, one of: DEV, STAGE, PROD. Default: PROD.")
parser.add_option("--ratiodenom",type="string",dest="ratiodenom",default=None,help="Label(s) to use, comma-separated, for ratio denominators.")
parser.add_option("--denomaspool",action="store_true",dest="denomaspool",default=False,help="Label denominator as POOL, only if a single ratio denominator is used. Default: False.")
parser.add_option("--labelbatch",type="string",dest="labelbatch",default=None,help="Label batch to use.")
parser.add_option("--s3",dest="userclone",action="store_true",default=False,help="Access RAW files by S3 (rclone). Default: False.")
parser.add_option("--rawfiles",type="string",dest="rawfiles",default=None,help="Regular expression for raw filenames, without the extention. For example, ^0[123].*0[12A]$ will match fractions 1, 2, and A, from analytical samples 1, 2, and 3 (for some studies).")

opts, args = parser.parse_args()

# opts.pdcapi = 'PROD'

if opts.ratiodenom:
    opts.ratiodenom = list(map(str.strip,opts.ratiodenom.split(',')))

if not opts.studyid:
    if len(args) < 1:
        parser.error("Require study id or submitter id.")
    study_id = args[0]
else:
    study_id = opts.studyid

assert study_id

if not opts.jobid:
    job_id = str(uuid.uuid4())
else:
    job_id = opts.jobid

assert re.search(r'^[a-zA-Z0-9_-]+$',job_id), "Bad --jobid: "+job_id

workdir = job_id

if os.path.exists(workdir):
    shutil.rmtree(workdir)


from PDC import PDC, PDCSTAGE, PDCDEV

if opts.pdcapi == "PROD":
    pdc = PDC()
elif opts.pdcapi == "DEV":
    pdc = PDCDEV()
elif opts.pdcapi == "STAGE":
    pdc = PDCSTAGE()
else:
    raise RuntimeError("Bad --pdcapi option: "+opts.pdcapi)

try:
    study = pdc.find_study(study_id,rawfnmatch=opts.rawfiles,labelbatch=opts.labelbatch,ratiodenom=opts.ratiodenom)
except ConnectionError as e:
    traceback.print_exc()
    raise RuntimeError("Can't access PDC API[%s]: %s"%(opts.pdcapi,pdc.graphql))

if opts.denomaspool:
    assert study.has_pool_label(), "Multiple denominators, cannot label as POOL"

def todict(lines):
    d = dict()
    for l in lines.splitlines():
        if not l.strip():
            continue
        key,value = list(map(str.strip,l.split(':',1)))
        d[key] = value
    return d

instrmap = todict("""
Q Exactive: Thermo Q-Exactive HCD
Orbitrap Velos: Thermo Velos HCD
Orbitrap Lumos: Thermo Q-Exactive HCD
Orbitrap Fusion Lumos: Thermo Q-Exactive HCD
Orbitrap Fusion: Thermo Q-Exactive HCD
Exactive Plus: Thermo Q-Exactive HCD
Thermo Orbitrap Q Exactive HF-X: Thermo Q-Exactive HCD
Q Exactive HF: Thermo Q-Exactive HCD
Q Exactive HF-X: Thermo Q-Exactive HCD
""")
exprtypemap = todict("""
iTRAQ4: iTRAQ
""")
taxonmap = todict("""
Homo sapiens: Human
""")
analytemap = todict("""
""")

exprtype = study.experiment_type()
exprtype = exprtypemap.get(exprtype,exprtype)

if exprtype == 'iTRAQ':
    labels = ['114','115','116','117']
    labelmap = {'itraq_114': '114',
                'itraq_115': '115',
                'itraq_116': '116',
                'itraq_117': '117'}
elif exprtype == 'TMT10':
    labels = ['126','127N','127C','128N','128C','129N','129C','130N','130C','131']
    labelmap = {'tmt_126':  '126',
                'tmt_127n': '127N',
                'tmt_127c': '127C',
                'tmt_128n': '128N',
                'tmt_128c': '128C',
                'tmt_129n': '129N',
                'tmt_129c': '129C',
                'tmt_130n': '130N',
                'tmt_130c': '130C',
                'tmt_131':  '131',
                }
elif exprtype == 'TMT11':
    labels = ['126C','127N','127C','128N','128C','129N','129C','130N','130C','131N','131C']
    labelmap = {'tmt_126':  '126C',
                'tmt_127n': '127N',
                'tmt_127c': '127C',
                'tmt_128n': '128N',
                'tmt_128c': '128C',
                'tmt_129n': '129N',
                'tmt_129c': '129C',
                'tmt_130n': '130N',
                'tmt_130c': '130C',
                'tmt_131':  '131N',
                'tmt_131c': '131C'
                }
elif exprtype == "Label Free":
    labels = ['000']
    labelmap = {'Label Free': '000'}
else:
    assert False, exprtype

analyte = study.analytical_fraction()
analyte = analytemap.get(analyte,analyte)

taxon = study.taxon()
if not taxon:
    taxon = "Human"
taxon = taxonmap.get(taxon,taxon)

instr = study.instrument()
instr = instrmap.get(instr,instr)

os.makedirs(workdir)
# basename = (job_id + "_" + analyte)
basename = job_id

wh = open("%s/%s.study.txt"%(workdir,basename),'w')
wh.write("ID: "+str(study.id())+"\n")
wh.write("SUBMITTER_ID: "+str(study.submitter_id())+"\n")
wh.write("SUBMITTER_NAME: "+str(study.name())+"\n")
wh.close()

wh2 = open("%s/%s.RAW.txt"%(workdir,basename),'w')
if opts.userclone:
    wh2.write('files\trclone\t%s.RAW.cksum\tpdc:pdcdatastore\n'%(basename,))
else:
    wh2.write('files\t%s\t%s.RAW.cksum\t%s\n'%(pdc.resource,basename,study.id()))
wh2.close()

wh = open("%s/%s.RAW.cksum"%(workdir,basename),'w')
wh1 = open("%s/%s.sample.txt"%(workdir,basename),'w')

headerrow = ["FileNameRegEx","AnalyticalSample"]
headerrow.extend(labels)
if study.has_ratios():
    if study.has_label_reagents():
        headerrow.append("LabelReagent")
    headerrow.append("Ratios")
headerrow.append("Fraction")
print("\t".join(headerrow),file=wh1)
for rf in study.rawfiles():
    if opts.userclone:
        print("\t".join([rf.get(k,"") for k in ['md5sum','sha1sum','file_size','file_location']]),file=wh)
    else:
        rf['_file_location'] = "/".join([rf['file_id'],rf['file_name']])
        print("\t".join([rf.get(k,"") for k in ['md5sum','sha1sum','file_size','_file_location']]),file=wh)
    # if not opts.userclone:
    #     assert rf.get('file_location') in rf.get('signedUrl')
    #     line = ["files","url","%s.RAW.cksum"%(basename,)]
    #     extra = {'filenameregex': "^%s$"%re.escape(rf.get('file_location')),
    #              'fullpathfmt': rf.get('signedUrl').replace('%','%%').replace(rf.get('file_location'),'%s')}
    #     line.append(";".join(map(lambda kv: "%s=%s"%kv,extra.items())))
    #     print("\t".join(line),file=wh2)
    ansamp = rf['plex_or_dataset_name']
    samplerow = ["^%s$"%re.escape(rf['file_name'].rsplit('.',1)[0]),
                 ":".join([ansamp,rf['study_run_metadata_id']])]
    samples = dict()
    for tag in labelmap:
        lab = labelmap[tag]
        asi = ":".join([rf[tag][0]['aliquot_submitter_id'].replace(" ",""),
                        rf[tag][0]['aliquot_run_metadata_id'].replace(" ","")])
        if opts.denomaspool and tag == study.pool_label(ansamp):
            asi = "POOL"
        samples[lab] = asi
    assert len(samples) == len(labels)
    for lab in labels:
        samplerow.append(samples[lab])
    if study.has_label_reagents() and study.label_reagent(ansamp):
        samplerow.append(study.label_reagent(ansamp))
    if study.has_ratios() and study.ratios(ansamp):
        ratios = []
        for n,d in study.ratios(ansamp):
            ratios.append("%s/%s"%(labelmap[n],labelmap[d]))
        samplerow.append(",".join(ratios))
    samplerow.append(rf['fraction_number'].strip())
    print("\t".join(samplerow),file=wh1)
wh.close()
wh1.close()
# if not opts.userclone:
#     wh2.close()

wh = open("%s/%s.params"%(workdir,basename,),'w')
print("SPECIES=\"%s\""%(taxon,), file=wh)
print("PROTEOME=\"%s\""%(analyte,), file=wh)
print("QUANT=\"%s\""%(exprtype,), file=wh)
if study.has_label_reagents():
    print("BATCH=\"%s\""%(" ".join([s.rsplit('.',1)[0] for s in study.label_reagents()])), file=wh)
print("INST=\"%s\""%(instr), file=wh)
wh.close()
study.write_label_reagents("%s"%(workdir,))

print("StudyID: "+study.id())
print("JobID:   "+workdir)
