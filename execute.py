#!bin/python
import sys, os, os.path, time, datetime, urllib, glob, tempfile, shutil, re, zipfile
from operator import itemgetter
from collections import defaultdict, Counter
from StringIO import StringIO

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning, InsecurePlatformWarning, SNIMissingWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(SNIMissingWarning)

scriptdir = os.path.split(os.path.abspath(sys.argv[0]))[0]

from clustermanager import ClusterManager
cm = ClusterManager()

from optparse import OptionParser, OptionGroup
parser = OptionParser()
advanced = OptionGroup(parser, "Advanced")

parser.add_option("--galaxy",dest="url",help="Galaxy server URL",default=None)
parser.add_option("--apikey",dest="apikey",help="Galaxy API key",default=None)
parser.add_option("--cluster",dest="cluster",help="Galaxy cluster name",default=None)
parser.add_option("--history",dest="hist",help="Galaxy history",default="Data Analysis Pipeline")
parser.add_option("--workflow",dest="wf",help="Galaxy workflow",default=None)
parser.add_option("--data",dest="data",action="append",help="Datafile collection file listing input files (resource, location, hashes) for batch execution.",default=None)
parser.add_option("--file",dest="file",action="append",help="Input file for upload to history for workflow execution input",default=None)
parser.add_option("--param",dest="param",action="append",help="Parameter for workflow execution",default=None)
parser.add_option("--outdir",dest="outdir",help="Output directory prefix. Default: None.",default=None)
parser.add_option("-i","--idle",dest="idle",type="int",default=2,
                  help="Max. idle workflow executions. Default: 2.")


advanced.add_option("--sleep",dest="sleep",type="int",default=60,
		    help="Time, in seconds, between polling the Galaxy history. Default: 60 seconds.")
advanced.add_option("--sched_sleep",dest="sched_sleep",type="int",default=15,
		    help="Time, in seconds, between polling the Galaxy server to check whether workflow input jobs have been added to the Galaxy history. Default: 15 seconds.")
advanced.add_option("--max_complete",dest="max_complete",type="int",default=-1,
		    help="Max. complete collections before forcing download. Default: No limit.")
advanced.add_option("--max_download",dest="max_download",type="int",default=-1,
		    help="Max. output file collections to download, per iteration. Default: No limit.")
advanced.add_option("--max_retries",dest="max_retries",type="int",default=3,
		    help="Max. retries to run the workflow for a datafile. Default: 3.")
advanced.add_option("--min_disk",dest="min_disk",type="float",default=0.1,
                  help="Min. disk space available to schedule a new workflow execution. Numbers between 0 and 1 indicate a proportion, numbers greater than 1 indicate Gb. Default: 10%.")
advanced.add_option("--remote",dest="remote",action="store_true",default=False,
	            help="Run batch execute script on AWS cluster, rather than locally. Default: False")
advanced.add_option("--remote_jobname",dest="remote_jobname",help="Remote batch execute script job name.",default=None)
advanced.add_option("--remote_nostatus",dest="remote_nostatus",action="store_true",default=False,
	            help="Start remote job only, no execution status. Default: False")
advanced.add_option("--terminate_when_done",dest="terminate",action="store_true",default=False,
	            help="Terminate cluster when finished. Default: False")
parser.add_option_group(advanced)
opts,args = parser.parse_args()

if not opts.url:

    cluster = cm.parse_cluster_arg(name=opts.cluster,type=None)

    url = cluster.get('URL')
    apikey = cluster.get('APIKey')
    password = cluster.get('Password')
    from bioblend.cloudman import CloudManInstance
    cmi = CloudManInstance(url,password)
    
else:

    assert(opts.url)
    assert(opts.apikey)

    url = opts.url
    apikey = opts.apikey
    cmi = None
    cluster = None

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.dataset_collections import CollectionDescription, HistoryDatasetElement
gi = GalaxyInstance(url=url,key=apikey)
gi.verify=False
gi.histories.set_max_get_retries(10)
gi.tools.set_max_get_retries(10)
gi.workflows.set_max_get_retries(10)
gi.datasets.set_max_get_retries(10)

wfname2id = {}
for wf in gi.workflows.get_workflows():
    if ' (imported from ' in wf['name']:
        wfname2id[wf['name'].split(' (imported from ',1)[0]] = wf['id']
    else:
        wfname2id[wf['name']] = wf['id']
    # print gi.workflows.show_workflow(wf['id'])
if not opts.wf or opts.wf not in wfname2id:
    if opts.wf:
	print >>sys.stderr, "Workflow \"%s\" not found.\n"%(opts.wf,)
    print >>sys.stderr, "Available workflows:"
    for wf in sorted(wfname2id):
	print >>sys.stderr, " ", wf
    sys.exit(1)

if opts.remote or opts.remote_jobname:
    if not cluster or cluster.get('Type') != 'Cloudman':
        print >>sys.stderr, "Remote execute only available on AWS Cloudman Galaxy clusters"
        sys.exit(1)
    args = dict()
    uploads = []
    if opts.file:
        args['file'] = []
        for f in opts.file:
            uploads.append(f)
            args['file'].append(os.path.split(f)[1])
    if opts.data:
	dirstocheck = set()
        args['data'] = []
        for f in opts.data:
            uploads.append(f)
            args['data'].append(os.path.split(f)[1])
	    dirstocheck.add(os.path.split(os.path.abspath(f))[0])
	for d in dirstocheck:
	    for fn in glob.glob(os.path.join(d,"*.cksum")):
		uploads.append(fn)

    jobid = opts.remote_jobname
    for a in ("idle","sleep","sched_sleep","max_complete","max_download"):
        if hasattr(opts,a) and getattr(opts,a):
            args[a] = getattr(opts,a)
    args['workflow'] = opts.wf
    if opts.param:
        args['param'] = []
        for p in opts.param:
            args['param'].append(p)
    jobid = cluster.setup_job(jobid,uploads,**args)
    cluster.start_job(jobid)
    if not opts.remote_nostatus:
        cluster.status_job(jobid)
    sys.exit(0)

wfinput = dict()
wf = gi.workflows.show_workflow(wfname2id[opts.wf])
for wfst in wf['steps'].values():
    index = 0
    if wfst.get('annotation'):
	index = int(wfst.get('annotation'))-1
    tool = wfst['tool_id']
    if tool == None and  wfst['type'] == 'data_input':
	tool = 'data_input'
    wfinput[(tool,index)] = wfst['id']

hi = None
if opts.hist:
    his = map(lambda h: h.get('id'),gi.histories.get_histories(name=opts.hist))
    if len(his) > 1:
	print >>sys.stderr, "Too many histories match: %s"%(opts.hist,)
	sys.exit(1)
    if len(his) == 1:
	hi = his[0]
    else:
        hi = gi.histories.create_history(opts.hist).get('id')
else:
    timestamp = datetime.datetime.now().ctime()
    opts.hist = 'Spectra' + ' (' + timestamp + ")"
    hi = gi.histories.create_history(opts.hist).get('id')

inputfiles = []
uploaded = set()
if opts.file:
  for i,f in enumerate(opts.file):
    fname = os.path.split(f)[1]
    fid = None
    for di in gi.histories.show_matching_datasets(hi,re.compile("^%s$"%(re.escape(fname),))):
        id,name,state,visible,deleted = map(di.get,('id','name','state','visible','deleted'))
	if visible and not deleted and state == "ok":
	    fid = id
	    break
    if not fid:
        fid = gi.tools.upload_file(f,hi,file_name=fname)['outputs'][0]['id']
    inputfiles.append((wfinput[('data_input',i)],fid))
    uploaded.add(fname)

inputparams = []
if opts.param:
  for par in opts.param:
    try:
        tool,index,field,value = par.split(':')
	index = int(index)-1
    except ValueError:
        tool,field,value = par.split(':')
	index = 0
    inputparams.append((wfinput[(tool,index)],field,value))

def getdone(history):
    notdone = set()
    all = set()
    for di in gi.histories.show_history(history,contents=True,deleted=False,visible=True,details=True):
	name,state = map(di.get,('name','state'))
        base1,extn = DatafileCollection.dssplit(name)
        if state != 'ok':
            notdone.add(base1)
        all.add(base1)
    return (all-notdone)

def geterror(history):
    error = set()
    for di in gi.histories.show_history(history,contents=True,deleted=False,visible=True,details=True):
	name,state = map(di.get,('name','state'))
        base1,extn = DatafileCollection.dssplit(name)
        if state == 'error':
            error.add(base1)
    return error

def remove(history,base):
    for di in gi.histories.show_matching_datasets(history,re.compile("^%s[-.]"%(re.escape(base),))):
        id,name,state,visible,deleted = map(di.get,('id','name','state','visible','deleted'))
	if name in uploaded:
	    continue
	gi.histories.delete_dataset(history,id)
	gi.histories.delete_dataset(history,id,purge=True)

def download(history,base):
        jobmetrics = defaultdict(dict)
	for di in gi.histories.show_matching_datasets(history,re.compile("^%s[-.]"%(re.escape(base),))):
	    id,name,state,visible,deleted = map(di.get,('id','name','state','visible','deleted'))
	    prov = gi.histories.show_dataset_provenance(history,di.get('id'))
	    if not deleted and prov['job_id'] not in jobmetrics:
	        job = gi.jobs.show_job(prov['job_id'],full_details=True)
                for metric in job['job_metrics']:
		    if metric['name'] == 'runtime_seconds':
		        jobmetrics[job.get('id')]['runtime'] = float(metric['raw_value'])
		    if metric['name'] == 'start_epoch':
		        jobmetrics[job.get('id')]['start'] = float(metric['raw_value'])
		    if metric['name'] == 'end_epoch':
		        jobmetrics[job.get('id')]['end'] = float(metric['raw_value'])
		create_time = datetime.datetime.strptime(di['create_time'],"%Y-%m-%dT%H:%M:%S.%f")
		create_seconds = (create_time - datetime.datetime.utcfromtimestamp(0)).total_seconds()
		jobmetrics[job.get('id')]['created'] = create_seconds
		if 'start' in jobmetrics[job.get('id')]:
		     jobmetrics[job.get('id')]['waiting'] = jobmetrics[job.get('id')]['start'] - jobmetrics[job.get('id')]['created']
		     jobmetrics[job.get('id')]['elapsed'] = jobmetrics[job.get('id')]['end'] - jobmetrics[job.get('id')]['start']
	        else:
		    firstline = None; lastline = None;
		    for l in prov['stdout'].splitlines():
			if firstline == None:
			    firstline = l.strip()
			lastline = l.strip()
		    if firstline != None and lastline != None:
			starttime = None; endtime = None;
		        if firstline.split()[-1] == "Start":
			    try:
			        starttime = datetime.datetime.strptime(firstline[1:].split(']')[0],"%a %b %d %H:%M:%S %Y")
			    except ValueError:
				pass
		        if lastline.split()[-1] == "Finish":
			    try:
			        endtime = datetime.datetime.strptime(lastline[1:].split(']')[0],"%a %b %d %H:%M:%S %Y")
			    except ValueError:
				pass
		        if starttime != None and endtime != None:
		            jobmetrics[job.get('id')]['runtime'] = (endtime-starttime).total_seconds()

	    # print id,name,state,visible,deleted,jobmetrics[prov['job_id']]
	    assert(state == 'ok' or deleted or not visible)
	    assert(base in items)
            if visible and not deleted and name not in uploaded:
		base,extn = DatafileCollection.dssplit(name)
		if opts.data:
		  dlpath = items[base][minposition]['results']+'/'+name
	        else:
		  dlpath = name
		if opts.outdir:
		    dlpath = os.path.join(opts.outdir,dlpath)
		try:
		    os.makedirs(os.path.split(dlpath)[0])
		except OSError:
		    pass
		if os.path.exists(dlpath):
		    i = 1
		    while os.path.exists(dlpath+".%d"%i):
			i += 1
		    dlpath += ".%d"%i
                print >>sys.stderr, "Downloading %s..."%(dlpath,),
	        gi.datasets.download_dataset(id,file_path=dlpath,use_default_filename=False,wait_for_completion=True)
		if name.endswith('.html'):
		  try:
		    zf = zipfile.ZipFile(dlpath)
		    tmpdir = tempfile.mkdtemp(suffix="",prefix=".",dir=os.getcwd())
		    zf.extractall(tmpdir)
		    zf.close()
		    os.unlink(dlpath)
		    name1 = name.replace('.html','_html.html')
		    if os.path.exists(os.path.join(tmpdir,name1)):
			shutil.copyfile(os.path.join(tmpdir,name1),dlpath)
		    shutil.rmtree(tmpdir)
	          except zipfile.BadZipfile:
		    pass
	        print >>sys.stderr, "done."
		if os.path.getsize(dlpath) == 0:
		    print >>sys.stderr, "WARNING: empty file %s"%(name,)
	        gi.histories.update_dataset(history,id,visible=False)
	        # print >>sys.stderr, "Marked %s hidden."%(name,)
	    gi.histories.delete_dataset(history,id)
	    gi.histories.delete_dataset(history,id,purge=True)
	    # print >>sys.stderr, "Deleted %s."%(name,)
        running_time = sum(map(lambda d: d.get('runtime',0.0),jobmetrics.values()))
        create_time = min(map(lambda d: d.get('created',1e+20),jobmetrics.values()))
        done_time = max(map(lambda d: d.get('end',0.0),jobmetrics.values()))
	return dict(running=running_time, start=create_time, finish=done_time)

def getstatus(history,histname,url,items):
    print >>sys.stderr, "Status: %s (%s) [%s]"%(histname,url,datetime.datetime.now().ctime())
    index = {}; nextindex = 1; wininprocess = set()
    basestatus = defaultdict(Counter)
    dsid2jobid = dict()
    jobs = defaultdict(lambda: defaultdict(set))
    for di in gi.histories.show_history(history,contents=True,deleted=False,visible=True,details=True):
	dsid,name,state = map(di.get,('id','name','state'))
        base,extn = DatafileCollection.dssplit(name)
	if not extn:
	    continue
	if base not in items:
	    continue
	if name in uploaded:
	    continue
	if state in ('queued','running'):
	    prov = gi.histories.show_dataset_provenance(history,dsid)
	    jobid,toolid = map(prov.get,('job_id','tool_id'))
	    dsid2jobid[dsid] = jobid
	    if toolid.endswith('_pulsar'):
		jobs['pulsar'][state].add(jobid)
	    elif toolid in ('cptacraw','data_manager_pulsar_nodes','data_manager_pulsar_nodes_remove','data_manager_pulsar_nodes_shutdown'):
		jobs['local'][state].add(jobid)
	    else:
		jobs['slurm'][state].add(jobid)
        if state in ('new','queued','running') and extn in ('mgf','mzXML','mzML.gz','raw'):
            wininprocess.add(base)
	if state in ('running','error',):
	    if base not in index:
		index[base] = nextindex
		nextindex += 1
	    print >>sys.stderr, " % 3d."%(index[base],),"\t".join([base,"%10s"%extn,state])
	basestatus[base][state] += 1
    all = set(); running = set(); done = set(); error = set()
    for base,counts in basestatus.items():
	all.add(base)
	if counts['ok'] == sum(counts.values()):
	    done.add(base)
	elif counts['error'] > 0:
	    error.add(base)
	elif counts['running'] > 0:
	    running.add(base)
    for pl in ('local','slurm','pulsar'):
	for st in ('queued','running','waiting','new'):
	    jobs[pl][st] = len(jobs[pl][st])
    return all,len(all-running-done-error),len(running),len(error),len(done),jobs

def getcmstatus(cmi):
    status = dict()
    st = cmi.get_status()
    du = st['disk_usage']
    status.update(zip(('disk_used','disk_total','disk_percent'),map(du.get,('used','total','used_percent'))))
    status['nodes'] = dict()
    for nd in cmi.get_nodes():
        name = nd.get('alias','master')
	try:
            status['nodes'][name] = 100*float(nd['ld'].split()[1])
	except:
	    status['nodes'][name] = 0
    return status

def nodekey(name):
    if name.startswith('w'):
	return int(name[1:])
    if name.startswith('p'):
	return 1000+int(name[1:])
    # master
    return 0

from dfcollection import DatafileCollection
items = DatafileCollection()
if opts.data != None:
    items.read(*opts.data)
    positions = sorted(items.positions())
elif opts.file != None:
    base,extn = DatafileCollection.dssplit(os.path.split(opts.file[0])[1])
    items = {base: {0: dict(filename=base+".psm",results="")}}
    positions = [0]
else:
    items = {"": {0: dict()}}
    positions = [0]

# print >>sys.stderr, items, positions

itembase = sorted(items.keys())
currentitem = 0
nitems = len(itembase)
minposition = positions[0]
downloaded = set()
skipped = set()
retries = defaultdict(int)

climit = 1e+20 if opts.max_complete <= 0 else opts.max_complete
ilimit = opts.idle
statistics = defaultdict(dict)

while True:

    allbase,idle,running,error,done,jobcnt = getstatus(hi,opts.hist,url,items)
    assert(len(allbase) == (idle+running+error+done))
    waiting = nitems-len(allbase)-len(skipped)-len(downloaded)
    failed = set(map(lambda t: t[0],filter(lambda t: t[1] >= opts.max_retries,retries.items())))
    print >>sys.stderr, "Workflows: Waiting %d, Idle %d, Running %d, Error %d, Complete %d, Downloaded %d, Skipped %d, Failed %d, Done %d, Total %d"%(waiting, idle, running, error, done, len(downloaded), len(skipped), len(failed), len(downloaded)+len(skipped),nitems)
    if cmi:
        st = getcmstatus(cmi)
        print >>sys.stderr, "Instances: " + ", ".join(map(lambda i: "%s [%.0f%%]"%(i,st['nodes'][i]),sorted(st['nodes'],key=nodekey)))
        print >>sys.stderr, "     Jobs: " + ", ".join(map(lambda st: st.title() + " " + "+".join(map(lambda pl: "%s"%(jobcnt[pl][st],), ('local','slurm','pulsar'))),('running','queued')))
        print >>sys.stderr, "     Disk: %s/%s [%s]"%(st['disk_used'],st['disk_total'],st['disk_percent'])
        disk_too_full = False
        if 0 < opts.min_disk < 1 and (100-float(st['disk_percent'].strip('%'))) < opts.min_disk*100.0:
	    disk_too_full = True
	elif opts.min_disk >= 1 and (float(st['disk_total'].strip('G'))-float(st['disk_used'].strip('G'))) < opts.min_disk:
	    disk_too_full = True
    else:
        print >>sys.stderr, "     Jobs: " + ", ".join(map(lambda st: st.title() + " " + "+".join(map(lambda pl: "%s"%(jobcnt[pl][st],), ('local','slurm','pulsar'))),('running','queued')))
        disk_too_full = False
    print >>sys.stderr, ""

    # Look for an item yet to be executed...
    passes = 0
    while passes <= 2:
	currentbase = itembase[currentitem]
	# print >>sys.stderr, items[currentbase]
	(filenames,folders) = map(lambda k: map(lambda d: d.get(k),map(lambda p: items[currentbase][p],positions)),["filename","results"])
	folder = folders[0] # only first one applies
	if opts.outdir:
	    folder = os.path.join(opts.outdir,folder)
        if len(glob.glob("%s/%s.*"%(folder,currentbase,))) > 0:
	    # print >>sys.stderr, "File%s %s skipped."%("s" if len(filenames)>1 else "",", ".join(filenames))
	    if currentbase not in downloaded:
	        skipped.add(currentbase)
	    currentitem += 1
	    if currentitem >= nitems:
	        passes += 1
		currentitem = 0
	    continue
	if currentbase in allbase:
	    # print >>sys.stderr, "File%s %s already executing."%("s" if len(filenames)>1 else "",", ".join(filenames))
	    currentitem += 1
	    if currentitem >= nitems:
	        passes += 1
		currentitem = 0
	    continue
	if opts.data and retries.get(currentbase,-1) >= opts.max_retries:
	    currentitem += 1
	    if currentitem >= nitems:
	        passes += 1
		currentitem = 0
	    continue
	    
	break

    # No workflows in process, and no items yet to be processed...
    if len(allbase) == len(failed) and passes >= 2:
        break

    if len(error) > 10:
	break

    if idle < ilimit and done < climit and passes < 2 and not disk_too_full:
	(md5hash,sha1hash,bytes,fullpath,filename,resource,username,base) = map(lambda k: map(lambda d: d.get(k),map(lambda p: items[currentbase][p],positions)),["md5hash","sha1hash","sizehash","filepath","filename","resource","username","base"])
	assert(len(set(base)) == 1)
	base = base.pop()
	if base not in allbase:
            # print "Upload %s"%(filename,)
            # id = gi.tools.put_url(url,hi,file_name=filename)['outputs'][0]['id']
	    # id = gi.tools.run_tool(hi,'cptacraw',dict(input=fullpath,sha1hash=sha1hash,md5hash=md5hash,sizehash=bytes,resource_conditional=dict(resource=opts.resource,user='edwardsnj')))['outputs'][0]['id']
	    # gi.histories.update_dataset(hi,id,visible=False)
            # print gi.histories.show_dataset(hi,id)
            # sys.exit(1)
            # inputs={'0':dict(src='hda', id=id)}
	    inputs={}; params={}
	    for i in range(len(fullpath)):
	      if not fullpath[i]:
		continue
	      params[wfinput[('cptacraw',i)]] = dict(input=fullpath[i],sha1hash=sha1hash[i],md5hash=md5hash[i],sizehash=bytes[i],resource=resource[i],user=username[i])
            for toolid,field,value in inputparams:
	      if toolid not in params:
		params[toolid] = dict()
	      params[toolid][field] = value
            for toolid,fid in inputfiles:
	      inputs[toolid] = dict(src='hda',id=fid)
	    if opts.data:
	        print >>sys.stderr, "Schedule %s on %s..."%(opts.wf,", ".join(filename)),
	    else:
	        print >>sys.stderr, "Schedule %s..."%(opts.wf,),
            gi.workflows.invoke_workflow(wfname2id[opts.wf],inputs,params,history_id=hi)
	    print >>sys.stderr, "done."
	    # statistics[currentbase]['start'] = time.time()
	    if True or opts.data:

                print >>sys.stderr, 'Waiting for %s...'%", ".join(filename),
                time.sleep(opts.sched_sleep)
	        while True:
		    count = 0
		    for di in gi.histories.show_matching_datasets(hi,re.compile(r"^%s[-.]"%(re.escape(currentbase),))):
			if di['name'] not in filename:
			    continue
		        if not di.get('purged',False) and not di.get('deleted',False):
		            count += 1
		    if count >= len(filename):
		        break
		    print >>sys.stderr, ".",
                    time.sleep(opts.sched_sleep)
	        print >>sys.stderr, "done.\n"

                print >>sys.stderr, 'Sleeping...',
	        time.sleep(opts.sleep)
                print >>sys.stderr, 'awake.\n'

	    currentitem += 1
	    if currentitem >= nitems:
		currentitem = 0
	    continue

    if done > 0:
	for i,base in enumerate(getdone(hi)):
	    if base in items:
	        statistics[base].update(download(hi,base))
		if 'start' in statistics[base]:
		    statistics[base]['name'] = base
		    statistics[base]['elapsed'] = statistics[base]['finish'] - statistics[base]['start'] 
		    statistics[base]['elapsed_hours'] = round(statistics[base]['elapsed']/3600.0,2)
		    statistics[base]['attempts'] = retries.get(base,0)+1
		    statistics[base]['running_hours'] = round(statistics[base]['running']/3600.0,2)
		    statistics[base]['idle'] = max(0.0,statistics[base]['elapsed'] - statistics[base]['running'])
		    statistics[base]['idle_hours'] = max(0.0,statistics[base]['elapsed_hours'] - statistics[base]['running_hours'])
		    print >>sys.stderr, "%(name)s: elapsed %(elapsed_hours).2f hrs, running %(running_hours).2f hrs, idle %(idle_hours).2f hrs, attempts %(attempts)d"%statistics[base]
	        downloaded.add(base)
		if base in retries:
		    del retries[base]
	    if opts.max_download > 0 and (i+1) >= opts.max_download:
		break
	print >>sys.stderr, ""
	continue

    if error > len(failed):
	for base in geterror(hi):
	    if base in failed:
		continue
	    retries[base] += 1
	    if retries.get(base,-1) < opts.max_retries:
	        print >>sys.stderr, "Removing workflow jobs due to error: %s"%(base,)
	        # remove all files for this base from the history
	        remove(hi,base)
	print >>sys.stderr, ""
	continue

    print >>sys.stderr, 'Sleeping...',
    time.sleep(opts.sleep)
    print >>sys.stderr, 'awake.\n'


if opts.terminate and opts.cluster:
   import subprocess
   scriptdir = os.path.split(os.path.abspath(sys.argv[0]))[0]
   scriptextn = ''
   if sys.argv[0].endswith('.py'):
       scriptextn = '.py'
   cmd = [ os.path.join(scriptdir,'terminate%s'%(scriptextn,)), opts.cluster ]
   subprocess.call(cmd)

exitcode = 0
for base in retries:
    if retries.get(base,-1) > 0:
        print >>sys.stderr, "Dataset %s failed %d times, analysis not complete."%(base,retries[base])
        exitcode = 1

print >>sys.stderr, "Done."
sys.exit(exitcode)

