#!bin/python
import sys, os, os.path, time, datetime, urllib, glob, re, zipfile, tempfile, shutil
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
parser.add_option("--history",dest="hist",help="Galaxy history",default=None)
parser.add_option("--directory",dest="directory",help="Download directory",default=".")
parser.add_option("--stdout",dest="stdout",action="store_true",default=False)
parser.add_option("--stderr",dest="stderr",action="store_true",default=False)
parser.add_option("--regex",dest="regex",type="string",default=None)
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

if opts.regex:
    opts.regex = re.compile(opts.regex)

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.dataset_collections import CollectionDescription, HistoryDatasetElement
gi = GalaxyInstance(url=url,key=apikey)
gi.verify=False

hi = None
if opts.hist:
    his = map(lambda h: h.get('id'),gi.histories.get_histories(name=opts.hist))
    if len(his) > 1:
	print >>sys.stderr, "Too many histories match: %s"%(opts.hist,)
	sys.exit(1)
    elif len(his) == 1:
	hi = his[0]
    else:
        print >>sys.stderr, "No histories match: %s"%(opts.hist,)


if not os.path.exists(opts.directory):
    os.makedirs(opts.directory)

for di in gi.histories.show_history(hi,contents=True,deleted=False,visible=True,details=True):
    id,name,state,visible,deleted = map(di.get,('id','name','state','visible','deleted'))
    if not visible or deleted:
	continue
    if opts.regex != None and not opts.regex.search(name):
	continue
    if state == 'ok':
        filepath = os.path.join(opts.directory,name)
        i = 0
        while os.path.exists(filepath):
            i += 1
            filepath = "%s.%d"%(os.path.join(opts.directory,name),i)
        print >>sys.stderr, "Downloading %s..."%(name,),
	gi.datasets.download_dataset(id,file_path=filepath,use_default_filename=False,wait_for_completion=True)
        if name.endswith('.html'):
            try:
                zf = zipfile.ZipFile(filepath)
                tmpdir = tempfile.mkdtemp(suffix="",prefix=".",dir=os.getcwd())
                zf.extractall(tmpdir)
                zf.close()
                os.unlink(filepath)
                name1 = name.replace('.html','_html.html')
                if os.path.exists(os.path.join(tmpdir,name1)):
                    shutil.copyfile(os.path.join(tmpdir,name1),filepath)
                shutil.rmtree(tmpdir)
            except zipfile.BadZipfile:
                pass
	print >>sys.stderr, "done."

        if not opts.stdout and not opts.stderr:
	    continue
	
	stdoutdata,stderrdata = map(gi.histories.show_dataset_provenance(hi,id).get,["stdout","stderr"])
	if opts.stdout and stdoutdata.strip():
            print >>sys.stderr, "Downloading %s..."%(name+'.stdout',),
	    wh = open(filepath+'.stdout','w')
	    wh.write(stdoutdata)
	    wh.close()
	    print >>sys.stderr, "done."
	if opts.stderr and stderrdata.strip():
            print >>sys.stderr, "Downloading %s..."%(name+'.stderr',),
	    wh = open(filepath+'.stderr','w')
	    wh.write(stderrdata)
	    wh.close()
	    print >>sys.stderr, "done."
