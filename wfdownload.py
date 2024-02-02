#!bin/python
import sys, os, os.path, time, datetime, urllib.request, urllib.parse, urllib.error, glob, json, shutil
from operator import itemgetter
from collections import defaultdict, Counter
import configparser
from io import StringIO

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
    config = configparser.SafeConfigParser()
    config.read(['.galaxy.ini'])

    if not opts.cluster or not config.has_section(opts.cluster):
        if opts.cluster and not config.has_section(opts.cluster):
            print("Cluster \"%s\" not found.\n"%(opts.cluster,), file=sys.stderr)
        print("Available clusters:", file=sys.stderr)
        for sec in config.sections():
            if sec == 'GENERAL':
                continue
            print(" ",sec, file=sys.stderr)
        sys.exit(1)

    url = config.get(opts.cluster,'URL') + '/galaxy/'
    apikey = config.get(opts.cluster,'APIKey')

else:

    assert(opts.apikey)

    url = opts.url
    apikey = opts.apikey

from bioblend import ConnectionError
from bioblend.galaxy import GalaxyInstance
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
        wfdict = gi.workflows.export_workflow_dict(wfname2id[wfname])
    except ConnectionError:
        print("Cannot download workflow %s"%(wfname,), file=sys.stderr)
        continue
    wfdict['name'] = wfname
    for key in list(wfdict['steps']):
        wfdict['steps'][int(key)] = wfdict['steps'][key]
        del wfdict['steps'][key]
    if 'uuid' in wfdict:
        del wfdict['uuid']
    for st in wfdict['steps']:
        if 'workflow_outputs' in wfdict['steps'][st]:
            wfdict['steps'][st]['workflow_outputs'] = sorted(wfdict['steps'][st]['workflow_outputs'],key=lambda d: d.get('output_name'))
    for st in wfdict['steps']:
        if 'position' in wfdict['steps'][st]:
            for k,v in wfdict['steps'][st]['position'].items():
                wfdict['steps'][st]['position'][k] = round(v,6)
   
    wfstr = json.dumps(wfdict,sort_keys=True,indent=4)
    wffilepath = os.path.join(opts.directory,wffilename)
    if os.path.exists(wffilepath):
        oldwfstr = open(wffilepath).read()
        if wfstr != oldwfstr:
            print("Workflow %s modified, writing new workflow file"%(wfname,), file=sys.stderr)
            shutil.move(wffilepath,wffilepath+'.bak')
        else:
            continue
    else:
        print("Workflow %s is new, writing workflow file"%(wfname,), file=sys.stderr)
    wh = open(wffilepath,'w')
    wh.write(wfstr.rstrip())
    wh.write('\n')
    wh.close()
