#!bin/python

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning, InsecurePlatformWarning, SNIMissingWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(SNIMissingWarning)

from bioblend.cloudman import CloudManInstance

from boto.s3.connection import S3Connection, OrdinaryCallingFormat
from boto.ec2.connection import EC2Connection
from boto.cloudformation.connection import CloudFormationConnection
from boto.exception import EC2ResponseError
from boto.ec2.cloudwatch import CloudWatchConnection

import re, datetime, time

class AWSResources(object):

    def __init__(self,access_key,secret_key,cluster_name=None,config=None):
        self.ec2conn = EC2Connection(access_key,secret_key)
        self.s3conn = S3Connection(access_key,secret_key,calling_format=OrdinaryCallingFormat())
        self.cfconn = CloudFormationConnection(access_key,secret_key)
        self.cwconn = CloudWatchConnection(access_key,secret_key)
        self.config = config
        self.cmi = None
        self.bucket = None
        self.master = None
        self.workers = []
        self.winpulsar = []
        self._cpu = dict()
        self._load = dict()
        self.cfstacks = set()
        self.volume = None
        self.volume_usage = None
        self.publicip = None
        self.starttime = None
        if cluster_name:
            self.set_cluster_name(cluster_name,self.config)

    def set_cluster_name(self,cluster_name,config=None):
        self.cluster_name = cluster_name
        if not config:
            config = self.config
        self.bucket = None
        self.master = None
        self.workers = []
        self.winpulsar = []
        self._cpu = dict()
        self._load = dict()
        self.cfstacks = set()
        self.volume = None
        self.publicip = None
        self.starttime = None
        if config and config.has_section(cluster_name):
            password = config.get(cluster_name,'password')
            url = config.get(cluster_name,'url')
            self.cmi = CloudManInstance(url,password)
            # print self.cmi.get_static_state()
        self.set_bucket()
        self.set_instances()
        self.set_volume()
        self.set_stacks()

    def get_cluster_names(self):

        names = set()
        for b in self.s3conn.get_all_buckets():
            if re.search(r'^cm-[a-f0-9]{32}$',b.name):
                if self.s3conn.lookup(b.name) is None:
                    continue
                for it in b.list():
                    if it.key.endswith('.clusterName'):
                        names.add(it.key.split('.')[0])

        for resv in self.ec2conn.get_all_reservations():
            inst = resv.instances[0]
            if inst.state == 'terminated':
                continue
            if inst.tags.get('clusterName'):
                names.add(inst.tags.get('clusterName'))

        for vol in self.ec2conn.get_all_volumes():
            name = vol.tags.get('Name')
            if name:
                names.add(name)
                continue
            bname = vol.tags.get('bucketName')
            if bname and re.search(r'^cm-[a-f0-9]{32}$',bname):
                b = self.s3conn.lookup(bname)
                if b is None:
                    continue
                for it in b.list():
                    if it.key.endswith('.clusterName'):
                        names.add(it.key.split('.')[0])

        for stack in self.get_all_stacks():
            if stack.stack_status != 'DELETE_COMPLETE':
                for param in stack.parameters:
                    if param.key == 'ClusterName':
                        names.add(param.value)

        return sorted(names)

    def get_all_stacks(self):
        next_token = None
        while True:
            stacks = self.cfconn.describe_stacks(next_token=next_token)
            for stack in stacks:
                yield stack
            next_token = stacks.next_token
            if not next_token:
                break

    def set_bucket(self):
        for b in self.s3conn.get_all_buckets():
            if b.get_key("%s.clusterName"%(self.cluster_name,)):
                self.bucket = b.name

    def get_bucket(self):
        return self.bucket

    def bucket_exists(self):
        if self.bucket and self.s3conn.lookup(self.bucket) is not None:
            return True
        return False

    def load(self):
        # print self.cmi.get_nodes()
        self._load = {}
        if self.cmi:
            try:
                for nd in self.cmi.get_nodes():
                    try:
                        self._load[nd['id']] = 100*float(nd['ld'].split()[1])
                    except:
                        pass
            except:
                pass

    def cpu(self,id):
        try:
            self._cpu[id] = float(self.cwconn.get_metric_statistics(300, datetime.datetime.utcnow() - datetime.timedelta(seconds=2*600),
                                                                datetime.datetime.utcnow(), 'CPUUtilization', 'AWS/EC2', 'Average',
                                                                dimensions={'InstanceId':id})[-1]['Average'])
        except IndexError:
            self._cpu[id] = 0

    def set_instances(self):
        for resv in self.ec2conn.get_all_instances():
            inst = resv.instances[0]
            if inst.state == 'terminated':
                continue
            if inst.tags.get('clusterName') == self.cluster_name:
                if inst.tags['role'] == 'master':
                    self.master = inst.id
                    self.cpu(inst.id)
                    self.publicip = inst.ip_address
                    # print inst.launch_time
                    # 2018-03-20T15:09:49.000Z
                    self.starttime = datetime.datetime.strptime(inst.launch_time.split('.',1)[0],"%Y-%m-%dT%H:%M:%S")
                    # print self.starttime
                    # print 'Found master instance:',inst.id,inst.state
                    # print self.cwconn.list_metrics(dimensions={'InstanceId':inst.id})
                    # self.cpupercent = self.cwconn.get_metric_statistics(300, datetime.datetime.utcnow() - datetime.timedelta(seconds=2*600),
                    #                                       datetime.datetime.utcnow(), 'CPUUtilization', 'AWS/EC2', 'Average',
                    #                                         dimensions={'InstanceId':inst.id})[-1]['Average']
                elif inst.tags['role'] == 'worker':
                    self.workers.append(inst.id)
                    self.cpu(inst.id)
                    # print 'Found Worker instance:',inst.id,inst.state
            elif inst.tags.get('Name') == 'WinPulsar: %s'%(self.cluster_name,):
                self.winpulsar.append(inst.id)
                self.cpu(inst.id)
                stid = inst.tags['aws:cloudformation:stack-id']
                self.cfstacks.add(stid)
                # print 'Found WinPulsar instance:',inst.id,inst.state
                # print 'Found CloudFormation stack:',stid,cfconn.describe_stacks(stid)[0].stack_status
        self.load()

    def instance_exists(self,id):
        assert(id != None)
        inst = self.ec2conn.get_all_instances(id)[0].instances[0]
        return (inst.state != 'terminated')

    def get_master(self):
        return self.master

    def master_exists(self):
        return self.master != None and self.instance_exists(self.master)

    def get_workers(self):
        return self.workers

    def worker_exists(self):
        return sum(map(int,list(map(self.instance_exists,self.workers))))

    def get_winpulsar(self):
        return self.winpulsar

    def winpulsar_exists(self):
        return sum(map(int,list(map(self.instance_exists,self.winpulsar))))

    def set_volume(self):
        for vol in self.ec2conn.get_all_volumes():
            if (vol.tags.get('Name') == self.cluster_name) and ((not self.bucket) or vol.tags.get('bucketName') == self.bucket):
                self.volume = vol.id
        if self.cmi:
            try:
                st = self.cmi.get_status()
                du = st['disk_usage']
                self.volume_usage = list(map(du.get,('used_percent','used','total')))
            except:
                pass

    def get_volume(self):
        return self.volume

    def volume_exists(self):
        if not self.volume:
            return False
        try:
            return (self.ec2conn.get_all_volumes(self.volume)[0].status != 'Deleted')
        except (IndexError,EC2ResponseError):
            return False

    def set_stacks(self):
        for stack in self.get_all_stacks():
            if stack.stack_status != 'DELETE_COMPLETE':
                for param in stack.parameters:
                    if param.key == 'ClusterName' and param.value == self.cluster_name:
                        self.cfstacks.add(stack.stack_id)

    def get_stacks(self):
        return self.cfstacks

    def astack_exists(self,id):
        return (self.cfconn.describe_stacks(id)[0].stack_status != 'DELETE_COMPLETE')

    def stack_exists(self):
        return sum(map(int,list(map(self.astack_exists,self.cfstacks))))

    def any_resources(self):
        return self.master_exists() or self.worker_exists() or self.winpulsar_exists() or \
               self.stack_exists() or self.volume_exists() or self.bucket_exists()

    def delete_resources(self):
        print("Checking for master..."); sys.stdout.flush()
        if self.master_exists():
            print("Terminating master..."); sys.stdout.flush()
            self.ec2conn.terminate_instances(instance_ids=[self.master])
        print("Checking for workers..."); sys.stdout.flush()
        instances = []
        for iid in self.workers:
            if self.instance_exists(iid):
                instances.append(iid)
        if len(instances) > 0:
            print("Terminating workers..."); sys.stdout.flush()
            self.ec2conn.terminate_instances(instance_ids=instances)
        print("Checking for bucket..."); sys.stdout.flush()
        if self.bucket_exists():
            print("Deleting bucket..."); sys.stdout.flush()
            bucket = self.s3conn.lookup(self.bucket)
            bucket.delete_keys(list([it.key for it in bucket.list()]),quiet=True)
            self.s3conn.delete_bucket(self.bucket)
        print("Checking for stacks..."); sys.stdout.flush()
        if self.stack_exists():
            print("Deleting stacks..."); sys.stdout.flush()
            for sid in self.cfstacks:
                self.cfconn.delete_stack(sid)
        print("Checking for master..."); sys.stdout.flush()
        if self.master_exists():
            print("Waiting for master to terminate..."); sys.stdout.flush()
            counter = 0
            while self.master_exists() and counter < 6:
                time.sleep(10)
                counter += 1
        print("Checking for volume..."); sys.stdout.flush()
        if self.volume_exists():
            print("Deleting volume..."); sys.stdout.flush()
            self.ec2conn.delete_volume(volume_id=self.volume)
        print("Checking for stacks..."); sys.stdout.flush()
        if self.stack_exists():
            print("Waiting for stacks to be deleted..."); sys.stdout.flush()
            counter = 0
            while self.stack_exists() and counter < 6:
                time.sleep(10)
                counter += 1
        print("Checking for winpulsar instances..."); sys.stdout.flush()
        instances = []
        for iid in self.winpulsar:
            if self.instance_exists(iid):
                instances.append(iid)
        if len(instances) > 0:
            print("Terminating winpulsar instances..."); sys.stdout.flush()
            self.ec2conn.terminate_instances(instance_ids=instances)
        print("Checking for any remaining resources..."); sys.stdout.flush()
        if self.any_resources():
            print("Waiting for resources to be deleted..."); sys.stdout.flush()
            counter = 0
            while self.any_resources() and counter < 6:
                time.sleep(10)
                counter += 1
            print("Checking for any remaining resources..."); sys.stdout.flush()
        return (not self.any_resources())

    def __str__(self):
        s = ""
        if self.master_exists() or self.worker_exists() or self.winpulsar_exists():
            s += "Instances: "
            needcomma = False
            if self.master_exists():
                if self.cmi:
                    s += "master (%s) [CPU:%.0f%%]"%(self.publicip,self._load.get(self.master,0))
                else:
                    s += "master (%s) [CPU:%.0f%%]"%(self.publicip,self._cpu.get(self.master,0))
                needcomma = True
            n = self.worker_exists()
            if n > 0:
                if needcomma:
                    s += ", "
                if n == 1:
                    s += "worker"
                else:
                    s += "%d*workers"%(n,)
                if self.cmi:
                    s += " [CPU:%s]"%(",".join(["%.0f%%"%(self._load.get(w,0),) for w in self.workers]),)
                else:
                    s += " [CPU:%s]"%(",".join(["%.0f%%"%(self._cpu.get(w,0),) for w in self.workers]),)
                needcomma = True
            n = self.winpulsar_exists()
            if n > 0:
                if needcomma:
                    s += ", "
                if n == 1:
                    s += "winpulsar"
                else:
                    s += "%d*winpulsar"%(n,)
                s += " [CPU:%s]"%(",".join(["%.0f%%"%(self._cpu.get(w,0),) for w in self.winpulsar]),)
            s += '\n'
        if self.stack_exists() or self.volume_exists() or self.bucket_exists():
            s += "Other: "
            needcomma = False
            if self.volume_exists():
                s += 'volume'
                if self.volume_usage != None:
                    s += " [%s/%s,%s]"%(self.volume_usage[1],self.volume_usage[2],self.volume_usage[0])
                needcomma = True
            if self.bucket_exists():
                if needcomma:
                    s += ", "
                s += 'bucket'
                needcomma = True
            n = self.stack_exists()
            if n > 0:
                if needcomma:
                    s += ", "
                if n == 1:
                    s += 'stack'
                else:
                    s += "%d*stacks"%(n,)
                needcomma = True
            s += '\n'
        if self.master_exists():
            s1 = str(datetime.datetime.utcnow()-self.starttime).rsplit('.',1)[0]
            s += "Uptime: %s\n"%(s1,)
        s = s.rstrip('\n')

        # print "Master:",aws.get_master(),aws.master_exists()
        # print "Workers:",", ".join(aws.get_workers()),aws.worker_exists()
        # print "Stacks:",", ".join(aws.get_stacks()),aws.stack_exists()
        # print "WinPulsar:",", ".join(aws.get_winpulsar()),aws.winpulsar_exists()
        # print "Bucket:",aws.get_bucket(),aws.bucket_exists()
        # print "Volume:",aws.get_volume(),aws.volume_exists()

        return s


if __name__ == '__main__':

    import sys, os, os.path, time
    import configparser, urllib.request, urllib.parse, urllib.error

    scriptdir = os.path.split(os.path.abspath(sys.argv[0]))[0]

    config = configparser.SafeConfigParser()
    found = config.read([os.path.join(scriptdir,'.galaxy.ini'),'.galaxy.ini'])
    assert len(found)>0, "Can't find .galaxy.ini"

    assert config.has_section('GENERAL')
    general = dict(config.items('GENERAL'))

    access_key = general['aws_access_key']
    secret_key = general['aws_secret_key']

    aws = AWSResources(access_key,secret_key,config=config)

    monitor = None
    if len(sys.argv) > 1 and sys.argv[1] == "-n":
        monitor = int(sys.argv[2])
        sys.argv.pop(1)
        sys.argv.pop(1)

    if len(sys.argv) == 3 and sys.argv[2] == "--delete":
        aws.set_cluster_name(sys.argv[1])
        print("Cluster:",sys.argv[1])
        sys.stdout.flush()
        print(aws)
        sys.stdout.flush()
        print("Deleting...")
        sys.stdout.flush()
        aws.delete_resources()
        print("Done.")
        print("Cluster:",sys.argv[1])
        sys.stdout.flush()
        print(aws)
        sys.stdout.flush()

    cluster_name = None
    if len(sys.argv) > 1:
        first = True
        while True:
            aws.set_cluster_name(sys.argv[1])
            if monitor != None:
                if not first:
                    print()
                print("[%s]"%(datetime.datetime.now().ctime(),))
            if aws.any_resources():
                print(aws)
                sys.stdout.flush()
                first = False
            if monitor == None:
                break
            time.sleep(monitor)

    else:
        for cn in aws.get_cluster_names():
            aws.set_cluster_name(cn)
            print("Cluster: %s\n%s\n"%(cn,aws))
