#!bin/python

import sys, os, os.path, time

from clustermanager import ClusterManager
cm = ClusterManager()
for name in cm.getclusternames(type=None):
    cluster = cm.getcluster(name,type=None)
    print "%s: %s"%(name,cluster.get('URL'))
