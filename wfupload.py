#!bin/python
import sys, os, os.path, time, datetime, urllib, glob, json, traceback
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
parser.add_option("--directory",dest="directory",help="Workflows directory",default="workflows")
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

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.dataset_collections import CollectionDescription, HistoryDatasetElement
import bioblend
gi = GalaxyInstance(url=url,key=apikey)
gi.verify=False

for wffile in sorted(glob.glob(os.path.join(opts.directory,'*.ga'))):
  try:
      wfi = gi.workflows.import_workflow_from_local_path(wffile)
      print "Imported workflow: %s"%(wfi['name'],)
  except:
      print "Import workflow failed: %s"%(wffile,)
      traceback.print_exc()
