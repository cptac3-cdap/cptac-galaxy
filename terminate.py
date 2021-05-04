#!bin/python

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning, InsecurePlatformWarning, SNIMissingWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(SNIMissingWarning)

from bioblend.cloudman import CloudManInstance

import sys, os, os.path, time
from clustermanager import ClusterManager

cm = ClusterManager()

cluster_name = None
if len(sys.argv) > 1:
    cluster_name = sys.argv[1]

cluster = cm.parse_cluster_arg(cluster_name)
cluster_name = cluster.get('Name')

cluster_password = cluster.get('Password')
url = cluster.get('URL')
apikey = cluster.get('APIKey')

from bioblend.galaxy import GalaxyInstance
gi = GalaxyInstance(url=url,key=apikey)
gi.verify=False

# Delete all histories so that the pulsar shutdown job can run...
for h in gi.histories.get_histories():
    gi.histories.delete_history(h.get('id'), purge=True)

# Schedule the shutdown job...
hi = gi.histories.create_history('Shutdown').get('id')
cfid = gi.tools.run_tool(hi,'data_manager_pulsar_nodes_shutdown',{})['outputs'][0]['id']

# and wait for it to complete...
delay=15
while True:
    ok = 0
    print("Shutdown WinPulsar nodes:", end=' ')
    di = gi.histories.show_dataset(hi,cfid)
    print(di['state'])
    sys.stdout.flush()
    if di['state'] == 'ok':
        break
    time.sleep(delay)
print("Shutdown WinPulsar nodes: done")

# shutdown the cloudman cluster...

cmi = CloudManInstance(url,cluster_password)
try:
    cmi.terminate(terminate_master_instance=True, delete_cluster=True)
except requests.exceptions.ReadTimeout:
    pass

access_key = cm.get('aws_access_key')
secret_key = cm.get('aws_secret_key')

from awsresources import AWSResources
aws = AWSResources(access_key,secret_key,cluster_name)

print("Waiting for AWS cleanup...")
maxwait = 5
start = time.time()
clean = True
while aws.any_resources():
    if (time.time() - start) > 60*maxwait:
        clean = False
        break
    print("Cluster: %s\n%s\n"%(cluster_name, aws))
    time.sleep(15)

if not clean:
    print("AWS cleanup not complete after %s minutes"%(maxwait,), file=sys.stderr)
    print("Remaining resources:\n%s"%(aws,), file=sys.stderr)
else:
    print("AWS cleanup done.")

cm.remove(cluster)
