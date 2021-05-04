#!bin/python
import sys

from clustermanager import ClusterManager
cm = ClusterManager()

if not cm.has('aws_keypath'):
    print >>sys.stderr, "Path to AWS SSH key file not in configuration file"
    sys.exit(1)

cluster_name = None
if len(sys.argv) > 1:
    cluster_name = sys.argv[1]

cluster = cm.parse_cluster_arg(cluster_name)

jobnames = []
for line in cluster.execute("ls -d /home/ubuntu/galaxy-scratch/*",output=True):
    print >>sys.stderr, line
    jobname = line.strip().rsplit('/',1)[-1]
    jobnames.append(jobname)

jobname = None
if len(sys.argv) > 2:
    jobname = sys.argv[2]
    if jobname not in jobnames:
	jobname = None
elif len(jobnames) == 1:
    jobname = jobnames[0]
if not jobname:
    print >>sys.stderr, "Need a jobname to monitor..."
    for n in sorted(jobnames):
	print >>sys.stderr, "  %s"%(n,)
    sys.exit(1)

remotedir = "/home/ubuntu/galaxy-scratch/" + jobname
for line in cluster.execute("tail -f %s/execute.log"%(remotedir,),output=True):
    print >>sys.stderr, line
