#!bin/python
import sys, os, os.path, time, datetime, urllib, glob, json, shutil
from operator import itemgetter
from collections import defaultdict, Counter
import ConfigParser
from StringIO import StringIO

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning, InsecurePlatformWarning, SNIMissingWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(SNIMissingWarning)

from optparse import OptionParser
parser = OptionParser()
parser.add_option("--galaxy",dest="url",help="Galaxy server URL",default=None)
parser.add_option("--apikey",dest="apikey",help="Galaxy API key",default=None)
parser.add_option("--cluster",dest="cluster",help="Galaxy cluster name",default=None)
parser.add_option("--directory",dest="directory",help="Download directory",default="workflows")
opts,args = parser.parse_args()

if not opts.url:

    assert os.path.exists('.galaxy.ini')
    config = ConfigParser.SafeConfigParser()
    config.read(['.galaxy.ini'])

    if not opts.cluster or not config.has_section(opts.cluster):
        if opts.cluster and not config.has_section(opts.cluster):
	    print >>sys.stderr, "Cluster \"%s\" not found.\n"%(opts.cluster,)
	print >>sys.stderr, "Available clusters:"
	for sec in config.sections():
	    if sec == 'GENERAL':
		continue
	    print >>sys.stderr, " ",sec
        sys.exit(1)

    url = config.get(opts.cluster,'URL')
    apikey = config.get(opts.cluster,'APIKey')

else:

    assert(opts.apikey)

    url = opts.url
    apikey = opts.apikey

from bioblend import ConnectionError
from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.dataset_collections import CollectionDescription, HistoryDatasetElement
gi = GalaxyInstance(url=url,key=apikey)
gi.verify=False

wfname2id = {}
for wf in gi.workflows.get_workflows():
    if ' (imported from ' in wf['name']:
        wfname2id[wf['name'].split(' (imported from ',1)[0]] = wf['id']
    else:
        wfname2id[wf['name']] = wf['id']

if not os.path.exists(opts.directory):
    os.makedirs(opts.directory)
for wfname in wfname2id:
    wffilename = 'Galaxy-Workflow-%s.ga'%(wfname.replace(' ','_').replace('+','_'),)
    try:
        wfdict = gi.workflows.export_workflow_json(wfname2id[wfname])
    except ConnectionError:
        print >>sys.stderr, "Cannot download workflow %s"%(wfname,)
        continue
    wfdict['name'] = wfname
    for key in list(wfdict['steps']):
	wfdict['steps'][int(key)] = wfdict['steps'][key]
	del wfdict['steps'][key]
    wfstr = json.dumps(wfdict,sort_keys=True,indent=4)
    wffilepath = os.path.join(opts.directory,wffilename)
    if os.path.exists(wffilepath):
	oldwfstr = open(wffilepath).read()
	if wfstr != oldwfstr:
	    print >>sys.stderr, "Workflow %s modified, writing new workflow file"%(wfname,)
	    shutil.move(wffilepath,wffilepath+'.bak')
	else:
	    continue
    else:
	print >>sys.stderr, "Workflow %s is new, writing workflow file"%(wfname,)
    wh = open(wffilepath,'w')
    wh.write(wfstr)
    wh.close()
