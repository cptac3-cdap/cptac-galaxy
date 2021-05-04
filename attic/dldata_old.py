#!bin/python
import sys, os, os.path, time, datetime
from operator import itemgetter
from collections import defaultdict, Counter

from optparse import OptionParser
parser = OptionParser()
parser.add_option("--galaxy",dest="url",help="Galaxy server URL",default=None)
parser.add_option("--username",dest="user",help="Galaxy user",default=None)
parser.add_option("--password",dest="pw",help="Galaxy password",default=None)
parser.add_option("--history",dest="hist",help="Galaxy history",default=None)
opts,args = parser.parse_args()

if opts.url == None:
    print >>sys.stderr, "--galaxy option required."
    sys.exit(1)

if opts.user == None:
    print >>sys.stderr, "--username option required."
    sys.exit(1)

if opts.pw == None:
    print >>sys.stderr, "--password option required."
    sys.exit(1)

if opts.hist == None:
    print >>sys.stderr, "--history option required."
    sys.exit(1)

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.dataset_collections import CollectionDescription, HistoryDatasetElement
gi = GalaxyInstance(url=opts.url,email=opts.user,password=opts.pw)

hi = None
if opts.hist:
    his = map(lambda h: h.get('id'),gi.histories.get_histories(name=opts.hist))
    if len(his) > 1:
	print >>sys.stderr, "Too many histories match: %s"%(opt.hist,)
	sys.exit(1)
    if len(his) ==1:
	hi = his[0]
    else:
	print >>sys.stderr, "No histories match: %s"%(opt.hist,)
	sys.exit(1)

def dssplit(name):
    base,extn = name.rsplit('.',1)
    if extn == 'gz':
	base,extn1 = base.rsplit('.',1)
	extn = extn1+'.gz'
    return base,extn

def download(history,base,extn):
    for di in gi.histories.show_matching_datasets(history,"%s.%s"%(base,extn)):
	id,name,state = map(di.get,('id','name','state'))
	assert(state == 'ok')
        print >>sys.stderr, "Downloading %s..."%(name,),
	gi.datasets.download_dataset(id,file_path=name,use_default_filename=False,wait_for_completion=True)
	print >>sys.stderr, "done."

def getdone(history,extn):
    done = set()
    basestatus = defaultdict(Counter)
    for di in gi.histories.show_history(history,contents=True,deleted=False,visible=True,details=True):
	name,state = map(di.get,('name','state'))
        base,extn = dssplit(name)
	if state == 'ok':
	    done.add(base)
    return done

for extn in args:
     for base in getdone(hi,extn):
	download(hi,base,extn)
