#!bin/python

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning, InsecurePlatformWarning, SNIMissingWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(SNIMissingWarning)

import time
import sys, os, os.path, re
import getpass
import datetime
import hashlib
import glob
from lockfile import FileLock
from collections import defaultdict
import configparser
import traceback

scriptdir = os.path.split(os.path.abspath(sys.argv[0]))[0]
scriptextn = ''
if sys.argv[0].endswith('.py'):
    scriptextn = '.py'

defaults = configparser.SafeConfigParser()
found = defaults.read([os.path.join(scriptdir,'.defaults.ini')])
assert len(found)>0, "Can't find .default.ini"
assert defaults.has_section('GENERAL')
default = dict(defaults.items('GENERAL'))

from clustermanager import ClusterManager

try:
    cm = ClusterManager()
except AssertionError:
    # generally because .galaxy.ini hasn't been created yet...
    print("Configuration file .galaxy.ini not found.\nPlease run the CPTAC-Galaxy configure tool first!", file=sys.stderr)
    sys.exit(1)

general = dict(list(cm.items()))

from optparse import OptionParser, OptionGroup
parser = OptionParser()
advanced = OptionGroup(parser, "Advanced")
parser.add_option("--winpulsar",dest="winpulsar",type="int",default=1,
                  help="Number of Windows Pulsar nodes to start. Default: 1")
parser.add_option("--workers",dest="workers",type="int",default=2,
                  help="Max. worker nodes for autoscale. Default: 2")
parser.add_option("--master",dest="master",type="choice",
                  choices=["True","False","Auto"],
                  default="Auto",
                  help="Whether master should run jobs. One of True, False, Auto. Default: Auto.")

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
    print("Usage: launch%s [options] <Cluster-Name>"%(scriptextn,), file=sys.stderr)
    sys.exit(1);

cluster_name = args[0]
if not re.search(r'^[-A-Za-z0-9]+$',cluster_name):
    print("Cluster name %s has characters other than A-Z, a-z, 0-9, and \"-\"."%(cluster_name,), file=sys.stderr)
    sys.exit(1)

if cm.getcluster(cluster_name):
    print("Cluster name %s already used in this directory"%(cluster_name,), file=sys.stderr)
    sys.exit(1)

access_key = general['aws_access_key']
secret_key = general['aws_secret_key']

from awsresources import AWSResources
aws = AWSResources(access_key,secret_key,cluster_name)

if aws.any_resources():
    print("Cluster name %s already used in this AWS account"%(cluster_name,), file=sys.stderr)
    sys.exit(1)

cluster_password = getpass.getpass()
apikey = hashlib.md5((cluster_password+'\n').encode()).hexdigest()

import yaml
yaml.warnings({'YAMLLoadWarning': False})

from bioblend.cloudman import CloudManConfig
from bioblend.cloudman import CloudManInstance

baseurl='/'.join([default['tools_baseurl'],default['tools_version']])
prestarturl = baseurl + "/prestartcmd.sh"
installurl = baseurl + "/install.sh"
workerinstallurl = baseurl + "/install_worker.sh"

image_id = default['aws_imageid']
instance_type = general['aws_instance_type']

extra = dict(
        # no_start=True,
        use_ssl=True,
        master_prestart_commands=[
                "wget -O - -q --no-check-certificate %s | /bin/sh"%(prestarturl,)
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
                "archive_md5": "256ea4fd4c211d40085f2af018fc6019",
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
    print("[%02d:%02d]"%(elapsed/60,elapsed%60), end=' ')
    status = cmi.get_machine_status()
    if status.get('public_ip'):
        print("IP:",status['public_ip'], end=' ')
    if status.get('instance_state'):
        print("Status:",status['instance_state'], end=' ')
    print()
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

cluster = cm.getcluster(cluster_name)

cmi = CloudManInstance(url,cluster_password,verify=False,authuser="ubuntu")
cloudman_seen = False
while True:
    elapsed = int((datetime.datetime.now() - start).seconds)
    print("[%02d:%02d]"%(elapsed/60,elapsed%60), end=' ')
    print("IP:",publicip, end=' ')
    try:
        pss = None; galaxy = None;
        status = cmi._make_get_request("get_all_services_status",timeout=15)
        # print(status)
        pss = status.get('PSS');
        galaxy = status.get('Galaxy')
        if pss:
            print("PSS:",pss, end=' ')
        if galaxy:
            print("Galaxy:",galaxy, end=' ')
        cloudman_seen = True
    except Exception as e:
        # traceback.print_exc()
        pass
    print()
    sys.stdout.flush()
    if not cloudman_seen and elapsed > 10*60:
        print("Force starting cloudman...")
        cluster.ssh_session_start()
        for line in cluster.execute('sudo /opt/cloudman/boot/cm_boot.py restart'):
            print(line)
        cluster.ssh_session_end()
    if pss == 'Completed' and galaxy == 'Running':
        break
    time.sleep(delay)

print("Disable ProFTPd for security reasons...")
params = dict(service_name='ProFTPd',to_be_started='False')
cmi._make_get_request('manage_service',parameters=params)

print("Galaxy ready: %s"%(url+'/galaxy/',))

from bioblend.galaxy import GalaxyInstance
import bioblend

gi = GalaxyInstance(url=url+'/galaxy/',key=apikey)
gi.verify=False
gi.histories.set_max_get_retries(10)
gi.histories.set_get_retry_delay(20)

workflowsdir = 'workflows'
if not os.path.isdir(workflowsdir):
    workflowsdir = os.path.join(scriptdir,workflowsdir)
assert os.path.isdir(workflowsdir), "Can't find workflows directory: %s"%(workflowsdir,)

for wffile in sorted(glob.glob('%s/*.ga'%(workflowsdir,)),reverse=True):
    try:
        wfi = gi.workflows.import_workflow_from_local_path(wffile)
        print("Imported workflow: %s"%(wfi['name'],))
    except (requests.ConnectionError,bioblend.ConnectionError):
        print("Failed to import workflow file: %s"%(wffile,))
        traceback.print_exc()
        time.sleep(4)
    time.sleep(1)

start = datetime.datetime.now()
hi = gi.histories.create_history('Setup').get('id')
ids = defaultdict(set)
if opts.winpulsar > 0:
    print("Starting WinPulsar nodes...")
    args = {"cond|type": "aws", "cond|count": opts.winpulsar}
    id = gi.tools.run_tool(hi,'data_manager_pulsar_nodes',args)['outputs'][0]['id']
    ids['WinPulsar'].add(id)

print("Uploading sequence databases...")
from configparser import SafeConfigParser
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
        seqid = filename.rsplit('.',1)[0]
        species = seqconf.get(sdb,'Species',fallback='Unknown')
        source = seqconf.get(sdb,'Source',fallback='Unknown')

        try:
            id = gi.tools.upload_file(os.path.join(seqdbdir,filename),hi,file_name=filename)['outputs'][0]['id']; ids['SeqDB'].add(id)
            time.sleep(1)
            id = gi.tools.run_tool(hi,'data_manager_fetch_history_proteome',dict(display=display,source=source,organism=species.lower(),tag=seqid,input_fasta=dict(src='hda',id=id)))['outputs'][0]['id']; ids['SeqDB'].add(id)
            time.sleep(1)
            print("%s: %s"%(display, filename))
        except (requests.ConnectionError,bioblend.ConnectionError):
            print("Failed to upload sequence file: %s"%(filename,))
            traceback.print_exc()
            time.sleep(3)

# Wait until all uploaded sequence databases are available...
while True:
    elapsed = int((datetime.datetime.now() - start).seconds)
    print("[%02d:%02d]"%(elapsed/60,elapsed%60), end=' ')
    print("URL:",url+'/galaxy',"SeqDB upload:", end=' ')
    freq = defaultdict(int)
    for id in ids['SeqDB']:
        try:
            di = gi.histories.show_dataset(hi,id)
            freq[di['state']] += 1
        except (requests.ConnectionError,bioblend.ConnectionError):
            pass
    for st in sorted(freq):
        print("%s(%d)"%(st,freq[st]), end=' ')
    print()
    if freq['ok'] == len(ids['SeqDB']):
        break
    if freq['error'] > 0:
        sys.exit(1)
    time.sleep(delay)

print("Starting sequence database indexing and other setup tasks...")
for sdb in seqconf.sections():
    filename=seqconf.get(sdb,'Fasta')
    assert(filename)
    seqid = filename.rsplit('.',1)[0]
    if seqconf.has_option(sdb,'MSGFPlusIndex') and seqconf.getboolean(sdb,'MSGFPlusIndex'):
        try:
            id = gi.tools.run_tool(hi,'data_manager_msgfplus_indexer1',dict(all_proteome_source=seqid))['outputs'][0]['id']; ids['Index'].add(id)
        except (requests.ConnectionError,bioblend.ConnectionError):
            pass
    if seqconf.has_option(sdb,'PeptideScanIndex') and seqconf.getboolean(sdb,'PeptideScanIndex'):
        try:
            id = gi.tools.run_tool(hi,'data_manager_compress_seq',dict(all_proteome_source=seqid))['outputs'][0]['id']; ids['Index'].add(id)
        except (requests.ConnectionError,bioblend.ConnectionError):
            pass

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
    print("[%02d:%02d]"%(elapsed/60,elapsed%60), end=' ')
    print("URL:",url+'/galaxy', end=' ')
    totalok = 0
    print("Indexing:", end=' ')
    freq = defaultdict(int)
    for id in ids['Index']:
        di = gi.histories.show_dataset(hi,id)
        freq[di['state']] += 1
    for st in sorted(freq):
        print("%s(%d)"%(st,freq[st]), end=' ')
    if freq['error'] > 0:
        raise RuntimeError("Problem with sequence database indexing")
    totalok += freq['ok']
    print("Other:", end=' ')
    freq = defaultdict(int)
    for id in ids['Other']:
        di = gi.histories.show_dataset(hi,id)
        freq[di['state']] += 1
    for st in sorted(freq):
        print("%s(%d)"%(st,freq[st]), end=' ')
    totalok += freq['ok']
    if freq['error'] > 0:
        raise RuntimeError("Problem with other setup job")
    print()
    if totalok == sum([len(ids[k]) for k in ('Index','Other')]):
        if opts.workers > 0:
            time.sleep(delay)
            print("Setting autoscale, max %d workers"%(opts.workers,))
            cmi.enable_autoscaling(maximum_nodes=opts.workers)
            time.sleep(10)
            if opts.master != "Auto":
                print("Force master as worker setting")
                cmi._make_get_request("toggle_master_as_exec_host",timeout=15)
                if opts.master == "True":
                    if not cmi.is_master_execution_host():
                        cmi.set_master_as_execution_host(True)
                elif opts.master == "False":
                    if cmi.is_master_execution_host():
                        cmi.set_master_as_execution_host(False)
        break
    time.sleep(delay)

if opts.workers > 0:
    print("Indexed sequence databases and auto-scale workers ready.")
else:
    print("Indexed sequence databases ready.")
if opts.winpulsar > 0:
    print("Windows pulsar nodes will come online shortly.")
