#!bin/python

import sys, os, os.path, time, glob

from clustermanager import ClusterManager
cm = ClusterManager()

def getjobid(cmd,args):
    jobids = cluster.list_jobids()
    if len(args) < 1:
        if len(jobids) > 1:
            print >>sys.stderr, "%s: Jobid required"%(cmd,)
            print "Cluster %s job IDs:"%(cluster.get('name'),)
            for jid in jobids:
                print "  "+jid
            sys.exit(1)
	elif len(jobids) == 0:
	    print >>sys.stderr, "%s: No jobs on cluster %s"%(cmd,cluster.get('name'))
            print >>sys.stderr, usage
	    sys.exit(1)
        else:
            jobid = jobids[0]
    else:
        jobid = args.pop(0)
        if jobid not in jobids:
            print >>sys.stderr, "Bad jobid",jobid
            print >>sys.stderr, usage
            sys.exit(1)
    return jobid

keywords = """
install
list
login
start
stop
clean
remove
status
verify
organize
download
files
upload
data
manifest
logfile
shortlog
update
version
cdap
rsync
""".split()

usage = """
Usage: cluster [ <clustername> ] cdap [ -a (Complete|mzML|PSM|Reports) ] <param-file>
       cluster [ <clustername> ] list
       cluster [ <clustername> ] status [ all ]
       cluster [ <clustername> ] status [ <jobid> [ all ] ]
       cluster [ <clustername> ] logfile [ <jobid> [ <logfile> ] ]
       cluster [ <clustername> ] shortlog [ <jobid> [ <logfile> ] ]
       cluster [ <clustername> ] start [ <jobid> | all ]
       cluster [ <clustername> ] clean [ <jobid> [ <rawfile> ] ]
       cluster [ <clustername> ] stop [ <jobid> | all ]
       cluster [ <clustername> ] remove [ <jobid> | all ]
       cluster [ <clustername> ] verify [ <jobid> ]
       cluster [ <clustername> ] organize [ <jobid> ]
       cluster [ <clustername> ] download <destdir> [ <jobid> ]
       cluster [ <clustername> ] download <destdir> <datatag> <datadir>
       cluster [ <clustername> ] upload <path>/<datadir> <datatag>
       cluster [ <clustername> ] upload <filepath> <jobid>
       cluster [ <clustername> ] data [ <datatag> ]
       cluster [ <clustername> ] files [ <jobid> ]
       cluster [ <clustername> ] manifest <datatag> <datadir>
       cluster [ <clustername> ] update <version> <tools_version>
       cluster [ <clustername> ] version
""".strip()

args = list(sys.argv[1:])
if len(args) < 1:
    print >>sys.stderr, usage
    sys.exit(1)

cluster_name = None
if not args[0] in keywords:
    cluster_name = args.pop(0)

cluster = cm.parse_cluster_arg(cluster_name)
# cluster.sshdebug(True)

if len(args) < 1:
    print >>sys.stderr, usage
    sys.exit(1)

cmd = args.pop(0)

if cmd not in keywords:
    print >>sys.stderr, usage
    sys.exit(1)

if cmd == "install":

    # No additional args
    cluster.install_tools()
    
elif cmd == "login":

    # No additional args
    cluster.login()

elif cmd == "version":

    # No additional args
    for k,v in sorted(cluster.version().items()):
	print "%s: %s"%(k,v)

elif cmd == "update":

    cluster.update(*args[:1])
    print ""
    for k,v in sorted(cluster.version().items()):
	print "%s: %s"%(k,v)

elif cmd == "list":

    # No additional args
    print "Cluster %s (%s) job IDs:"%(cluster.get('name'),cluster.get('url'))
    running = None
    for jid in cluster.list_jobids():
	if not running:
	    running = set(cluster.running_jobs())
        print "  "+jid+(" (running)" if jid in running else " (stopped)")    

elif cmd == "status":

    # No additional args implies status of all jobs
    if len(args) == 0 or (len(args) > 0 and args[0] == "all"):
	if len(args) > 0 and args[0] == "all":
            cluster.status_all(all=True)
	else:
            cluster.status_all()
    else:
        # get jobid from first argument if present
        jobid = getjobid(cmd,args[:1])
	if len(args) > 1 and args[1] == "all":
            cluster.status_job(jobid,all=True)
	else:
            cluster.status_job(jobid)

elif cmd == "start":

    if len(args) > 0 and args[0] == "all":
        cluster.start_all_jobs()
    else:
        # get jobid from first argument if present
        jobid = getjobid(cmd,args[:1])
        cluster.start_job(jobid)

elif cmd == "stop":

    if len(args) > 0 and args[0] == "all":
        cluster.stop_all_jobs()
    else:
        # get jobid from first argument if present
        jobid = getjobid(cmd,args[:1])
        cluster.stop_job(jobid)

elif cmd == "remove":

    if len(args) > 0 and args[0] == "all":
        cluster.remove_all_jobs()
    else:
        # get jobid from first argument if present
        jobid = getjobid(cmd,args[:1])
        cluster.remove_job(jobid)

elif cmd == "clean":

    # get jobid from first argument if present
    jobid = getjobid(cmd,args[:1])
    if len(args) == 2:
        cluster.clear_workflow_instance(jobid,args[1])
    else:
        cluster.clear_job(jobid)

elif cmd == "logfile":

    # get jobid from first argument if present
    jobid = getjobid(cmd,args[:1])
    if len(args) == 2:
        cluster.job_logfile(jobid,args[1])
    else:
        cluster.job_logfile(jobid)

elif cmd == "shortlog":

    # get jobid from first argument if present
    jobid = getjobid(cmd,args[:1])
    if len(args) == 2:
        cluster.job_logfile(jobid,args[1],100)
    else:
        cluster.job_logfile(jobid,"execute.log",100)

elif cmd == "verify":

    # get jobid from first argument if present
    jobid = getjobid(cmd,args[:1])
    cluster.verify_job_results(jobid)

elif cmd == "organize":

    # get jobid from first argument if present
    jobid = getjobid(cmd,args[:1])
    cluster.organize_job_results(jobid)
    dirnames = cluster.dirnames(jobid)
    print "Cluster %s data tag %s directories:"%(cluster.get('name'),jobid)
    for dn in dirnames:
        print "  "+dn
        
elif cmd == "upload":

    if os.path.isfile(args[0]):
	jobid = getjobid(cmd,args[1:2])
	cluster.upload_file(args[0],jobid)
	cluster.list_files(jobid)
    else:
        cluster.upload_data(args[0],args[1])
        cluster.data_manifest(args[1],os.path.split(args[0])[1])

elif cmd == "files":

    jobid = getjobid(cmd,args[:1])
    cluster.list_files(jobid)

elif cmd == "data":
    if len(args) < 1:
        datanames = cluster.datanames()
        print "Cluster %s data tags:"%(cluster.get('name'),)
        for dn in datanames:
            print "  "+dn
    else:
        dataname = args[0]
        datanames = cluster.datanames()
        if dataname not in datanames:
            print "%s: Bad data tag %s"%(cmd,dataname)
            print "Cluster %s data tags:"%(cluster.get('name'),)
            for dn in datanames:
                print "  "+dn
            sys.exit(1)
        dirnames = cluster.dirnames(dataname)
        print "Cluster %s data tag %s directories:"%(cluster.get('name'),dataname)
        for dn in dirnames:
            print "  "+dn
	
elif cmd == "manifest":

    dataname = args[0]
    datanames = cluster.datanames()
    if dataname not in datanames:
        print "%s: Bad data tag %s"%(cmd,dataname)
        print "Cluster %s data tags:"%(cluster.get('name'),)
        for dn in datanames:
            print "  "+dn
        sys.exit(1)
    dirname = args[1]
    dirnames = cluster.dirnames(dataname)
    if dirname not in dirnames:
        print >>sys.stderr, "%s: Bad data tag %s directory %s"%(cmd,dataname,dirname)
        print "Cluster %s data tag %s directories:"%(cluster.get('name'),dataname)
        for dn in dirnames:
            print "  "+dn
        sys.exit(1)
    cluster.data_manifest(dataname,dirname)

elif cmd == "download":
    
    try:
        destdir = args.pop(0)
    except IndexError:
	print >>sys.stderr, "%s: Local destination directory required."%(cmd,)
	print >>sys.stderr, usage
	sys.exit(1)
    if not os.path.exists(destdir):
	print >>sys.stderr, "%s: Local destination directory %s not found."%(cmd,destdir)
        print >>sys.stderr, usage
        sys.exit(1)
    datanames = cluster.datanames()
    jobnames = cluster.list_jobids()
    if len(args) > 0 and args[0] in datanames:
        dataname = args[0]
	if len(args) < 2:
	    if args[0] in jobnames:
	        jobid = getjobid(cmd,args[:1])
                cluster.download_job(jobid,destdir)
	    else:
	        print >>sys.stderr, "%s: Data directory for data tag %s required"%(cmd,dataname)
                print >>sys.stderr, usage
                sys.exit(1)
	else:
            dirnames = cluster.dirnames(dataname)
            dirname = args[1]
	    if dirname not in dirnames:
	        print >>sys.stderr, "%s: Data directory %s for data tag %s not found"%(cmd,dirname,dataname)
                print >>sys.stderr, usage
                sys.exit(1)
            cluster.download_data(destdir,dataname,dirname)
    else:
        jobid = getjobid(cmd,args[:1])
        cluster.download_job(jobid,destdir)

elif cmd == "cdap":

    params = args[-1]
    paramdir, paramfile = os.path.split(params)
    basename = paramfile.rsplit('.',1)[0]
    if basename in cluster.list_jobids():
	print >>sys.stderr, "Job id %s already in use."%(basename,)
	sys.exit(1)
    rawfile = os.path.join(paramdir,basename+".RAW.txt")
    samplefile = os.path.join(paramdir,basename+".sample.txt")
    labelfile = os.path.join(paramdir,basename+".label.txt")
    mzidfile = os.path.join(paramdir,basename+".mzIdentML.txt")
    qctsvfile = os.path.join(paramdir,basename+".qcmetrics.tsv")
    uploads = []
    for fn in [params,rawfile,samplefile,labelfile,mzidfile,qctsvfile]:
	if os.path.exists(fn):
	    uploads.append(fn)
    batch = []
    for l in open(params):
        if l.split('=',1)[0].strip() == "BATCH":
            batch = l.split('=',1)[1].strip()
            batch = batch.strip('"')
            batch = batch.split()
    for b in batch:
        uploads.append(os.path.join(paramdir,b+".txt"))
    for fn in glob.glob(os.path.join(paramdir,"*.cksum")):
	uploads.append(fn)
    args = ["execute_cdap_on_cluster.sh","-c",cluster.get('name')] + args[:-1] + ["files/%s.params"%(basename,)]
    kwargs = dict(uploads=uploads,jobid=basename)
    jobid = cluster.setup_script_job(*args,**kwargs)
    cluster.start_job(jobid)
    cluster.status_job(jobid)

else:

    if len(args) < 1:
        print >>sys.stderr, usage
        sys.exit(1)

