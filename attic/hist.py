#!bin/python
import sys, os, os.path, time, datetime, re
from operator import itemgetter
from collections import defaultdict, Counter
from urllib import urlopen

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning, InsecurePlatformWarning, SNIMissingWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(SNIMissingWarning)

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
gi.verify = False

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

# for di in gi.histories.show_matching_datasets(hi,'SG252258\+SC248809\.txt'):
#     print di
# sys.exit(1)

dataset = dict()
for di in gi.histories.show_history(hi,contents=True,deleted=False,details=True):
    did = di.get('id')
    # if di.get('deleted') or di.get('purged'):
    # 	continue
    dataset[did] = dict(di.items())
    print "di:",di
    ji = gi.histories.show_dataset_provenance(hi,did)
    print "ji:",ji
    # url = gi._make_url(gi.jobs)
    # url = '/'.join([url, ji.get('id'), "build_for_rerun"])
    # rerun_details = gi.jobs._get(url=url)
    # print "rr:",rerun_details
sys.exit(1)

# print
# jobs = dict()
# for ji in gi.jobs.get_jobs():
    # jid=ji.get('id')
    # job = dict(gi.jobs.show_job(jid).items())
    # # print jid,job['state']
    # for outid in map(itemgetter('id'),job['outputs'].values()):
	# if outid in dataset:
	    # # print "",outid,dataset[outid]['state']
	    # if 'jobs' not in dataset[outid]:
		# dataset[outid]['jobs'] = []
	    # dataset[outid]['jobs'].append(job)
# 
# print

def timestr(d,k):
    s = d.get(k)
    if not s:
	return ""
    return s.split('T')[1].split('.')[0]

def timedelta(d,k0,k1):
    t0 = datetime.datetime.strptime(d.get(k0),"%Y-%m-%dT%H:%M:%S.%f")
    t1 = datetime.datetime.strptime(d.get(k1),"%Y-%m-%dT%H:%M:%S.%f")
    delta = (t1-t0)
    hd = (delta.seconds/3600)
    md = ((delta.seconds%3600)/60)
    sd = (delta.seconds%60)
    msd = delta.microseconds
    return "%02d:%02d:%02d.%03d"%(hd,md,sd,msd/1000)

def getelapsed(self,did):
    data = urlopen(self.url[:-len("/api/datasets/") + 1] + "/datasets/" + did + "/show_params").read()
    print data
    m = re.search(r'<td>Job Start Time</td><td>(.*)</td>',data)
    if m:
	starttime = datetime.datetime.strptime(m.group(1),"%Y-%m-%d %h:%m:%s")
    m = re.search(r'<td>Job End Time</td><td>(.*)</td>',data)
    if m:
	endtime = datetime.datetime.strptime(m.group(1),"%Y-%m-%d %h:%m:%s")
    delta = (endtime-starttime)
    hd = (delta.seconds/3600)
    md = ((delta.seconds%3600)/60)
    sd = (delta.seconds%60)
    return (delta.seconds,hd,md,sd)

i = 1
for di in sorted(dataset,key=lambda di: int(dataset[di]['hid'])):
    # print di
    ds = dataset[di]
    td = getelapsed(gi.datasets,di)
    if ds.get('state') not in ('queued','new'):
        print ds.get('hid'),ds.get('name'),td[0]
