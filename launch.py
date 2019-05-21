#!bin/python

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning, InsecurePlatformWarning, SNIMissingWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(SNIMissingWarning)

import time
import sys, os, os.path
import getpass
import datetime
import hashlib
import glob
from lockfile import FileLock
from collections import defaultdict 
import ConfigParser

scriptdir = os.path.split(os.path.abspath(sys.argv[0]))[0]
scriptextn = ''
if sys.argv[0].endswith('.py'):
   scriptextn = '.py'

defaults = ConfigParser.SafeConfigParser()
found = defaults.read([os.path.join(scriptdir,'.defaults.ini')])
assert len(found)>0, "Can't find .default.ini"
assert defaults.has_section('GENERAL')
default = dict(defaults.items('GENERAL'))

from clustermanager import ClusterManager

try:
    cm = ClusterManager()
except AssertionError:
    # generally because .galaxy.ini hasn't been created yet...
    print >>sys.stderr, "Configuration file .galaxy.ini not found.\nPlease run the CPTAC-Galaxy configure tool first!"
    sys.exit(1)

general = dict(cm.items())

from optparse import OptionParser, OptionGroup
parser = OptionParser()
advanced = OptionGroup(parser, "Advanced")
parser.add_option("--winpulsar",dest="winpulsar",type="int",default=1,
                  help="Number of Windows Pulsar nodes to start. Default: 1")
parser.add_option("--workers",dest="workers",type="int",default=2,
                  help="Max. worker nodes for autoscale. Default: 2")

for k in sorted(general):
    if k in ('aws_instance_type','aws_storage_size','aws_ebs_optimized'):
        advanced.add_option("--%s"%(k,),dest=k,type="string",default=None,
		            help="Override %s config. Config: %s."%(k,general[k],))

for k in sorted(default):
    if k in ('tools_version',):
        advanced.add_option("--%s"%(k,),dest=k,type="string",default=default[k],
                            help="Override %s default. Default: %s."%(k,default[k]))

parser.add_option_group(advanced)
opts,args = parser.parse_args()

for k in general:
    if hasattr(opts,k) and getattr(opts,k) != None:
	general[k] = getattr(opts,k)

for k in default:
    if hasattr(opts,k) and getattr(opts,k) != None:
	default[k] = getattr(opts,k)

if len(args) < 1:
    print >>sys.stderr, "Usage: launch%s [options] <Cluster-Name>"%(scriptextn,)
    sys.exit(1);

cluster_name = args[0]

if cm.getcluster(cluster_name):
    print >>sys.stderr, "Cluster name %s already used in this directory"%(cluster_name,)
    sys.exit(1)

access_key = general['aws_access_key']
secret_key = general['aws_secret_key']

from awsresources import AWSResources
aws = AWSResources(access_key,secret_key,cluster_name)

if aws.any_resources():
    print >>sys.stderr, "Cluster name %s already used in this AWS account"%(cluster_name,)
    sys.exit(1)

cluster_password = getpass.getpass()
apikey = hashlib.md5(cluster_password+'\n').hexdigest()

from bioblend.cloudman import CloudManConfig
from bioblend.cloudman import CloudManInstance

baseurl='/'.join([default['tools_baseurl'],default['tools_version']])
prestarturl = baseurl + "/prestartcmd.sh"
installurl = baseurl + "/install.sh"
workerinstallurl = baseurl + "/install_worker.sh"

image_id = default['aws_imageid']
instance_type = general['aws_instance_type']

extra = dict(
	use_ssl=True,
	master_prestart_commands=[
		"wget -O - -q %s | /bin/sh"%(prestarturl,)
	],
	admin_users=[
		general['admin_email'],
	],
	post_start_script_url=installurl,
        worker_post_start_script_url=workerinstallurl,
	initial_cluster_type = 'Galaxy',
	storage_type = 'volume',
	storage_size = general['aws_storage_size'],
	iops = 20000 if bool(eval(general['aws_ebs_optimized'])) else None,
	ebs_optimized = bool(eval(general['aws_ebs_optimized'])),
	cloud_name='Amazon - Virginia',
	instance_reboot_timeout=1200,
	bucket_default = default['cloudman_bucket'],
 	cluster_templates=[
          {
            "filesystem_templates": [
              {
                "archive_url": "http://s3.amazonaws.com/%s/%s"%(default['cloudman_bucket'],default['galaxy_filesystem']),
                "type": "volume",
                "name": "galaxy",
                "roles": "galaxyTools,galaxyData",
                "size": "100"
              },
              {
                "mount_point": "/cvmfs/data.galaxyproject.org",
                "type": "cvmfs",
                "name": "galaxyIndices",
                "roles": "galaxyIndices"
              }
            ],
            "name": "Galaxy"
          }
       ],
)

cmc = CloudManConfig(
	access_key=access_key,
	secret_key=secret_key,
        cluster_name=cluster_name,
	image_id=image_id,
	subnet_id=general.get('aws_subnet'),
	instance_type=instance_type,
        password=cluster_password,
	cluster_type='Galaxy',
	key_name=general['aws_keyname'],
	**extra)
	
delay = 15
start = datetime.datetime.now()
cmi = CloudManInstance.launch_instance(cmc)
while True:
    elapsed = int((datetime.datetime.now() - start).seconds)
    print "[%02d:%02d]"%(elapsed/60,elapsed%60),
    status = cmi.get_machine_status()
    if status.get('public_ip'):
	print "IP:",status['public_ip'],
    if status.get('instance_state'):
	print "Status:",status['instance_state'],
    print
    sys.stdout.flush()
    if status['public_ip'] and status['instance_state'] == 'running':
	break
    time.sleep(delay)

publicip = status['public_ip']
url = "https://%s"%publicip

cluster = cm.newcluster(cluster_name)
cluster.set('Name',cluster_name)
cluster.set('Password',cluster_password)
cluster.set('APIKey',apikey)
cluster.set('PublicIP',publicip)
cluster.set('URL',url)
cluster.set('ToolsURL',baseurl)
cluster.set('Type','Cloudman')
cm.add(cluster)


cmi = CloudManInstance(url,cluster_password)
while True:
    elapsed = int((datetime.datetime.now() - start).seconds)
    print "[%02d:%02d]"%(elapsed/60,elapsed%60),
    print "IP:",publicip,
    try:
	pss = None; galaxy = None;
	status = cmi._make_get_request("get_all_services_status",timeout=15)
	pss = status.get('PSS'); 
	galaxy = status.get('Galaxy')
	if pss:
	    print "PSS:",pss,
	if galaxy:
	    print "Galaxy:",galaxy,
    except Exception, e: 
	pass
    print
    sys.stdout.flush()
    if pss == 'Completed' and galaxy == 'Running':
	break
    time.sleep(delay)

print "Galaxy ready: %s"%(url,)

from bioblend.galaxy import GalaxyInstance
gi = GalaxyInstance(url=url,key=apikey)
gi.verify=False
workflowsdir = 'workflows'
if not os.path.isdir(workflowsdir):
    workflowsdir = os.path.join(scriptdir,workflowsdir)
assert os.path.isdir(workflowsdir), "Can't find workflows directory: %s"%(workflowsdir,)

for wffile in sorted(glob.glob('%s/*.ga'%(workflowsdir,)),reverse=True):
  try:
      wfi = gi.workflows.import_workflow_from_local_path(wffile)
      print "Imported workflow: %s"%(wfi['name'],)
  except:
      print "Failed to import workflow file: %s"%(wffile,)
      traceback.print_exc()

start = datetime.datetime.now()
hi = gi.histories.create_history('Setup').get('id')
ids = defaultdict(set)
if opts.winpulsar > 0:
    print "Starting WinPulsar nodes..."
    args = {"cond|type": "aws", "cond|count": opts.winpulsar}
    id = gi.tools.run_tool(hi,'data_manager_pulsar_nodes',args)['outputs'][0]['id']
    ids['WinPulsar'].add(id)

print "Uploading sequence databases..."
from ConfigParser import SafeConfigParser
seqconf = SafeConfigParser()
seqdbdir = 'seqdb'
if not os.path.isdir(seqdbdir):
    seqdbdir = os.path.join(scriptdir,seqdbdir)
assert os.path.isdir(seqdbdir), "Can't find sequence database directory: %s"%(seqdbdir,)

seqdbini = os.path.join(seqdbdir,'seqdb.ini')
if os.path.exists(seqdbini):
  seqconf.read([seqdbini])
  for sdb in seqconf.sections():
    display=sdb
    filename=seqconf.get(sdb,'Fasta')
    assert(filename)
    print "%s: %s"%(display, filename)
    seqid = filename.rsplit('.',1)[0]
    species = seqconf.get(sdb,'Species','Unknown')
    source = seqconf.get(sdb,'Source','Unknown')
    id = gi.tools.upload_file(os.path.join(seqdbdir,filename),hi,file_name=filename)['outputs'][0]['id']; ids['SeqDB'].add(id)
    id = gi.tools.run_tool(hi,'data_manager_fetch_history_proteome',dict(display=display,source=source,organism=species.lower(),tag=seqid,input_fasta=dict(src='hda',id=id)))['outputs'][0]['id']; ids['SeqDB'].add(id)

# Wait until all uploaded sequence databases are available...
while True:
    elapsed = int((datetime.datetime.now() - start).seconds)
    print "[%02d:%02d]"%(elapsed/60,elapsed%60),
    print "URL:",url,"SeqDB upload:",
    freq = defaultdict(int)
    for id in ids['SeqDB']:
        di = gi.histories.show_dataset(hi,id)
        freq[di['state']] += 1
    for st in sorted(freq):                                                                                                                                  
        print "%s(%d)"%(st,freq[st]),
    print
    if freq['ok'] == len(ids['SeqDB']):
	break
    if freq['error'] > 0:
	sys.exit(1)
    time.sleep(delay)

print "Starting sequence database indexing and other setup tasks..."
for sdb in seqconf.sections():
    filename=seqconf.get(sdb,'Fasta')
    assert(filename)
    seqid = filename.rsplit('.',1)[0]
    if seqconf.has_option(sdb,'MSGFPlusIndex') and seqconf.getboolean(sdb,'MSGFPlusIndex'):
        id = gi.tools.run_tool(hi,'data_manager_msgfplus_indexer1',dict(all_proteome_source=seqid))['outputs'][0]['id']; ids['Index'].add(id)
    if seqconf.has_option(sdb,'PeptideScanIndex') and seqconf.getboolean(sdb,'PeptideScanIndex'):
        id = gi.tools.run_tool(hi,'data_manager_compress_seq',dict(all_proteome_source=seqid))['outputs'][0]['id']; ids['Index'].add(id)

if general.get('cptac_dcc_user','').strip():
    id = gi.tools.run_tool(hi,'data_manager_cptacdcc_login',dict(user=general['cptac_dcc_user'],password=general['cptac_dcc_password'],transfer="0"))['outputs'][0]['id']
    ids['Other'].add(id)

try:
    cluster = cm.getcluster(cluster_name)
    cluster.install_tools()
except AssertionError:
    pass

while True:
    elapsed = int((datetime.datetime.now() - start).seconds)
    print "[%02d:%02d]"%(elapsed/60,elapsed%60),
    print "URL:",url,
    totalok = 0
    print "Indexing:",
    freq = defaultdict(int)
    for id in ids['Index']:
        di = gi.histories.show_dataset(hi,id)
        freq[di['state']] += 1
    for st in sorted(freq):                                                                                                                                  
        print "%s(%d)"%(st,freq[st]),
    if freq['error'] > 0:
	raise RuntimeError("Problem with sequence database indexing")
    totalok += freq['ok']
    print "Other:",
    freq = defaultdict(int)
    for id in ids['Other']:
        di = gi.histories.show_dataset(hi,id)
        freq[di['state']] += 1
    for st in sorted(freq):                                                                                                                                  
        print "%s(%d)"%(st,freq[st]),
    totalok += freq['ok']
    if freq['error'] > 0:
	raise RuntimeError("Problem with other setup job")
    print
    if totalok == sum(map(lambda k: len(ids[k]),('Index','Other'))):
	if opts.workers > 0:
            print "Setting autoscale, max %d workers"%(opts.workers,)
            cmi.enable_autoscaling(maximum_nodes=opts.workers)
	    time.sleep(10)
            # print "Force master as exec host"
            # cmi._make_get_request("toggle_master_as_exec_host",timeout=15)
            # if not cmi.is_master_execution_host():
            #    cmi.set_master_as_execution_host(True)
	break
    time.sleep(delay)

if opts.workers > 0:
    print "Indexed sequence databases and auto-scale workers ready."
else:
    print "Indexed sequence databases ready."
if opts.winpulsar > 0:
    print "Windows pulsar nodes will come online shortly."
