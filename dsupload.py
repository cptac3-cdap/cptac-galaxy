#!bin/python
import sys, os, os.path, time, datetime, urllib.request, urllib.parse, urllib.error, glob, re
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
parser.add_option("--history",dest="hist",help="Galaxy history",default=None)
parser.add_option("--format",dest="format",help="Galaxy file format. Default: auto.",default=None)
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

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.dataset_collections import CollectionDescription, HistoryDatasetElement
gi = GalaxyInstance(url=url,key=apikey)
gi.verify=False

hi = None
if opts.hist:
    his = [h.get('id') for h in gi.histories.get_histories(name=opts.hist)]
    if len(his) > 1:
        print("Too many histories match: %s"%(opts.hist,), file=sys.stderr)
        sys.exit(1)
    elif len(his) == 1:
        hi = his[0]
    else:
        print("No histories match: %s"%(opts.hist,), file=sys.stderr)
        sys.exit(1)

for f in args:
    fname = os.path.split(f)[1]
    print("Uploading: %s"%(fname,))
    fid = None
    for di in gi.histories.show_matching_datasets(hi,fname):
        fid = di['id']
        break
    if not fid:
        fid = gi.tools.upload_file(f,hi,file_name=fname,file_type=opts.format)['outputs'][0]['id']
    else:
        print(sys.stderr, "File %f already in history"%(fname,))
