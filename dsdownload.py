#!bin/python
import sys, os, os.path, time, datetime, urllib.request, urllib.parse, urllib.error, glob, re, zipfile, tempfile, shutil
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
parser.add_option("--directory",dest="directory",help="Download directory",default=".")
parser.add_option("--stdout",dest="stdout",action="store_true",default=False)
parser.add_option("--stderr",dest="stderr",action="store_true",default=False)
parser.add_option("--regex",dest="regex",type="string",default=None)
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

if opts.regex:
    opts.regex = re.compile(opts.regex)

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


if not os.path.exists(opts.directory):
    os.makedirs(opts.directory)

for di in gi.histories.show_history(hi,contents=True,deleted=False,visible=True,details=True):
    id,name,state,visible,deleted = list(map(di.get,('id','name','state','visible','deleted')))
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
        print("Downloading %s..."%(name,), end=' ', file=sys.stderr)
        gi.datasets.download_dataset(id,file_path=filepath,use_default_filename=False)
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
        print("done.", file=sys.stderr)

        if not opts.stdout and not opts.stderr:
            continue

        stdoutdata,stderrdata = list(map(gi.histories.show_dataset_provenance(hi,id).get,["stdout","stderr"]))
        if opts.stdout and stdoutdata.strip():
            print("Downloading %s..."%(name+'.stdout',), end=' ', file=sys.stderr)
            wh = open(filepath+'.stdout','w')
            wh.write(stdoutdata)
            wh.close()
            print("done.", file=sys.stderr)
        if opts.stderr and stderrdata.strip():
            print("Downloading %s..."%(name+'.stderr',), end=' ', file=sys.stderr)
            wh = open(filepath+'.stderr','w')
            wh.write(stderrdata)
            wh.close()
            print("done.", file=sys.stderr)
