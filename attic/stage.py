#!bin/python

import sys, os, os.path, time

from clustermanager import ClusterManager
cm = ClusterManager()

if not cm.has('aws_keypath'):
    print >>sys.stderr, "Path to AWS SSH key file not in configuration file"
    sys.exit(1)

cluster_name = None
if len(sys.argv) > 1:
    cluster_name = sys.argv[1]

cluster = cm.parse_cluster_arg(cluster_name)

cluster.install_tools()
