#!bin/python

import sys, os, os.path, time

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
remove
status
verify
organize
download
upload
data
manifest
""".split()

usage = """
Usage: cluster [ <clustername> ] list
       cluster [ <clustername> ] status
       cluster [ <clustername> ] status [ <jobid> ]
       cluster [ <clustername> ] start [ <jobid> | all ]
       cluster [ <clustername> ] stop [ <jobid> | all ]
       cluster [ <clustername> ] remove [ <jobid> | all ]
       cluster [ <clustername> ] verify [ <jobid> ]
       cluster [ <clustername> ] organize [ <jobid> ]
       cluster [ <clustername> ] download <destdir> [ <jobid> ]
       cluster [ <clustername> ] download <destdir> <datatag> <datadir>
       cluster [ <clustername> ] upload <path>/<datadir> <datatag>
       cluster [ <clustername> ] data [ <datatag> ]
       cluster [ <clustername> ] manifest <datatag> <datadir>
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
    
elif cmd == "list":

    # No additional args
    print "Cluster %s job IDs:"%(cluster.get('name'),)
    running = set(cluster.running_jobs())
    for jid in cluster.list_jobids():
        print "  "+jid+(" (running)" if jid in running else " (stopped)")    

elif cmd == "status":

    # No additional args implies status of all jobs
    if len(args) == 0:
        cluster.status_all()
    else:
        # get jobid from first argument if present
        jobid = getjobid(cmd,args[:1])
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

    cluster.upload_data(args[0],args[1])
    cluster.data_manifest(args[1],os.path.split(args[0])[1])

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
    if len(args) > 0 and args[0] in datanames:
        dataname = args[0]
	if len(args) < 2:
	    print >>sys.stderr, "%s: Data directory for data tag %s required"%(cmd,dataname)
            print >>sys.stderr, usage
            sys.exit(1)
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

else:

    if len(args) < 1:
        print >>sys.stderr, usage
        sys.exit(1)

