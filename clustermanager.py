
# Management of local (.galaxy.ini) cluster data
import sys, os.path, tempfile, time, re, os
import ConfigParser
import subprocess
import lockfile

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning, InsecurePlatformWarning, SNIMissingWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(SNIMissingWarning)

from bioblend.galaxy import GalaxyInstance

class Cluster(object):
    remotebase = '/home/ubuntu/galaxy-scratch'
    datadir = remotebase + "/data"
    
    def __init__(self,**kw):
	self.attr = kw
        self._sshsession = None
        self._sshdebug = False

    def sshdebug(self,value=None):
        if value == None:
            return self._sshdebug
        self._sshdebug = value

    def get(self,key,default=None):
	if key.lower() in self.attr:
	    return self.attr[key.lower()]
	return default
	
    def set(self,key,value):
	self.attr[key.lower()] = value

    def has(self,key):
        return (key.lower() in self.attr)

    def items(self):
	return self.attr.items()

    ssh_session_start_cmd = "ssh -q -N -f -o \"ControlMaster=yes\" -o \"ControlPath=%(sshsession)s\" -i %(keypath)s -o \"StrictHostKeyChecking no\" ubuntu@%(ip)s"
    def ssh_session_start(self):
        publicip = self.get('publicip')
	assert(publicip)
	keypath = self.get('aws_keypath')
	assert(keypath)
        if self._sshsession != None:
            self.ssh_session_end()
        self._sshsession = os.path.abspath(".ubuntu@%(ip)s:22"%dict(ip=publicip))
	cmd = self.ssh_session_start_cmd%dict(ip=publicip,keypath=keypath,sshsession=self._sshsession)
        if self._sshdebug:
            print >>sys.stderr, "Execute: "+cmd
	subprocess.call(cmd, shell=True)

    ssh_session_end_cmd = "ssh -q -O exit -o \"ControlPath=%(sshsession)s\" ubuntu@%(ip)s 2>/dev/null"
    def ssh_session_end(self):
        publicip = self.get('publicip')
	assert(publicip)
	keypath = self.get('aws_keypath')
	assert(keypath)
	cmd = self.ssh_session_end_cmd%dict(sshsession=self._sshsession,ip=publicip)
        if self._sshdebug:
            print >>sys.stderr, "Execute: "+cmd
	subprocess.call(cmd, shell=True)
        self._sshsession = None


    copycmd = "scp -q -o \"ControlMaster=no\" -o \"ControlPath=%(sshsession)s\" \"%(fr)s\" ubuntu@%(ip)s:\"%(to)s\""
    def copy(self,fr,to):
	publicip = self.get('publicip')
	assert(publicip)
	keypath = self.get('aws_keypath')
	assert(keypath)
        if self._sshdebug:
            print >>sys.stderr, "Copy: %s to remote:%s"%(fr,to)
	cmd = self.copycmd%dict(ip=publicip,sshsession=self._sshsession,fr=fr,to=to)
	subprocess.call(cmd, shell=True)

    def execute(self,cmd,output=False):
        if not output:
            for line in self.execute_(cmd):
                pass
        else:
            return self.execute_(cmd)
	
    execcmd = "ssh -o \"ControlMaster=no\" -o \"ControlPath=%(sshsession)s\" ubuntu@%(ip)s \"%(cmd)s\""
    def execute_(self,cmd):
	publicip = self.get('publicip')
	assert(publicip)
	keypath = self.get('aws_keypath')
	assert(keypath)
        if self._sshdebug:
            print >>sys.stderr, "Executing: "+cmd
	cmd = self.execcmd%dict(ip=publicip,sshsession=self._sshsession,cmd=cmd)
        try:
            proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                yield line.rstrip()
        except KeyboardInterrupt:
            proc.terminate()
            raise

    logincmd = "ssh -i %(keypath)s -o \"StrictHostKeyChecking no\" ubuntu@%(ip)s"
    def login(self):
	publicip = self.get('publicip')
	assert(publicip)
	keypath = self.get('aws_keypath')
	assert(keypath)
	cmd = self.logincmd%dict(ip=publicip,keypath=keypath)
        print >>sys.stderr, "Executing: "+cmd
	subprocess.call(cmd, shell=True)

    rsynccmd = "rsync -avz --progress -e 'ssh -i %(keypath)s -o \"StrictHostKeyChecking no\"' ubuntu@%(ip)s:%(fr)s/ %(to)s"
    def rsync(self,fr,to):
	publicip = self.get('publicip')
        assert(publicip)
        keypath = self.get('aws_keypath')
        assert(keypath)
        rsynccmd = self.rsynccmd%dict(ip=publicip,keypath=keypath,fr=fr,to=to)
        if self._sshdebug:
            print >>sys.stderr, "Executing: "+rsynccmd
        subprocess.call(rsynccmd, shell=True)

    rsyncupcmd = "rsync -avz --progress -e 'ssh -i %(keypath)s -o \"StrictHostKeyChecking no\"' %(fr)s ubuntu@%(ip)s:%(to)s"
    def rsyncup(self,fr,to):
	publicip = self.get('publicip')
        assert(publicip)
        keypath = self.get('aws_keypath')
        assert(keypath)
	if not to.startswith('/'):
	    to = '/home/ubuntu/galaxy-scratch/data/' + to
	fr = fr.rstrip('/')
        rsyncupcmd = self.rsyncupcmd%dict(ip=publicip,keypath=keypath,fr=fr,to=to)
        if self._sshdebug:
            print >>sys.stderr, "Executing: "+rsyncupcmd
        subprocess.call(rsyncupcmd, shell=True)

    def dcccredentials(self):
        if self.get('cptac_dcc_user') and self.get('cptac_dcc_password'):
            f,fn = tempfile.mkstemp()
            os.close(f)
            fh = open(fn,'w')
            print >>fh, "[Portal]\nUser = %s\nPassword = %s\n"%(self.get('cptac_dcc_user'),self.get('cptac_dcc_password'))
            fh.close()
            self.copy(fn,".cptacdcc.ini")
            os.unlink(fn)

    def install_tools(self):
        assert self.get('type') == 'Cloudman'
        assert self.has('aws_keypath')
        scriptdir = self.get('_scriptdir')
        self.ssh_session_start()
        self.execute("mkdir -p cptac-galaxy")
        self.copy(os.path.join(scriptdir,"update.sh"),"cptac-galaxy/update.sh")
        self.copy(os.path.join(scriptdir,"VERSION"),"cptac-galaxy/VERSION")
        self.execute("echo \"linux-x86_64\" > cptac-galaxy/PLATFORM")
        self.execute("( cd cptac-galaxy; sh ./update.sh )")
        self.copy(os.path.join(scriptdir,".galaxy.ini"),"cptac-galaxy/.galaxy.ini")
        self.execute("rm -rf cptac-galaxy/cptacdcc")
        self.execute("wget -q -O - http://edwardslab.bmcb.georgetown.edu/software/downloads/CPTAC-DCC/cptacdcc.linux-x86_64.tgz | tar xzf - -C cptac-galaxy")
        self.dcccredentials()
        self.execute("mkdir -p " + self.datadir)
        self.ssh_session_end()

    def jobdir(self,jobid):
        return "%s/%s"%(self.remotebase,jobid)

    def setup_job(self,jobid=None,uploads=[],**args):
        if not jobid:
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            jobid = "batchjob-%s"%(ts,)
        else:
            assert not re.search(r'[^a-zA-Z0-9_.-]',jobid)
        assert jobid not in self.list_jobids()
        rdir = self.jobdir(jobid)
        self.ssh_session_start()
        self.execute('( mkdir -p %s; touch %s/execute.pid )'%(rdir,rdir))
        self.execute('mkdir -p %s/files'%(rdir,))
        self.execute('mkdir -p %s/results'%(rdir,))
        self.copy(".galaxy.ini",rdir + "/.galaxy.ini")
        self.execute("sed -i 's/%s/127.0.0.1/' "%(self.get('publicip'),)+ rdir + "/.galaxy.ini")

        for f in uploads:
            ff = os.path.split(f)[1]
            t = "/".join([rdir,'files',ff])
            self.copy(f,t)
        args['jobid'] = jobid
        args['remotedir'] = rdir
        args['name'] = self.get('name')
        args['outdir'] = '%s/results'%(rdir,)

        startscript = ("""
#!/bin/sh
cd %(remotedir)s
/home/ubuntu/cptac-galaxy/execute \\
    --cluster '%(name)s' \\
    --history '%(jobid)s' \\
    --outdir '%(outdir)s' \\
        """%args).strip()+"\n"
        for a in ("workflow","idle","sleep","sched_sleep","max_complete","max_download"):
            if args.get(a):
                startscript += "    --%s '%s' \\\n"%(a, args.get(a),)
        for f in args.get('file',[]):
            startscript += "    --file '%s/files/%s' \\\n"%(rdir,f,)
        for f in args.get('data',[]):
            startscript += "    --data '%s/files/%s' \\\n"%(rdir,f,)
        for p in args.get('param',[]):
            startscript += "    --param '%s' \\\n"%(p,)
        startscript += ("""
    >execute.log 2>&1 &
echo \"$!\" > execute.pid
        """).strip()
        
        f,fn = tempfile.mkstemp()
        os.close(f)
        fh = open(fn,'w')
        fh.write(startscript)
        fh.close()
        self.copy(fn,'%s/execute.sh'%(rdir,))
        os.unlink(fn)

        stopscript = ("""
#!/bin/sh
cd %(remotedir)s
kill -9 `cat execute.pid`
        """%args).strip()

        f,fn = tempfile.mkstemp()
        os.close(f)
        fh = open(fn,'w')
        fh.write(stopscript)
        fh.close()
        self.copy(fn,'%s/stop.sh'%(rdir,))
        os.unlink(fn)

        self.ssh_session_end()

        return jobid
        
    def list_jobids(self,needsession=True):
        jobids = []
        if needsession:
            self.ssh_session_start()
        for line in self.execute("ls -1d %s/*/execute.pid"%(self.remotebase,),output=True):
	    if line.count('/') < 2:
		continue
            jobid = line.rsplit('/',2)[1]
            if jobid == "*":
                continue
	    if jobid == "data":
		continue
            jobids.append(jobid)
        if needsession:
            self.ssh_session_end()
        return jobids

    def start_job(self,jobid):
        rdir = self.jobdir(jobid)
        self.ssh_session_start()
        self.execute("( sh %s/stop.sh; sh %s/execute.sh )"%(rdir,rdir,))
        self.ssh_session_end()

    def start_all_jobs(self):
        for jobid in self.list_jobids():
            self.start_job(jobid)

    def stop_job(self,jobid):
        self.ssh_session_start()
        self.execute("sh %s/stop.sh"%(self.jobdir(jobid),))
        self.ssh_session_end()

    def stop_all_jobs(self):
        for jobid in self.list_jobids():
            self.stop_job(jobid)

    def download_job(self,jobid,outdir):
	rdir = self.jobdir(jobid) + "/results"
	try:
	    os.makedirs(outdir)
	except OSError:
	    pass
	self.rsync(rdir,outdir)

    def verify_job_results(self,jobid):
        rdir = self.jobdir(jobid) + "/results"
        self.ssh_session_start()
        lastdir = None
        anybad = False
        for l in self.execute("cd %s; find . -name *.cksum -type f | sort"%(rdir,),output=True):
            if l.startswith('./'):
                l = l[2:]
            sl = os.path.split(l)
            if sl[0] != lastdir:
                if lastdir != None:
                    print ""
                print "%s: ."%(sl[0],),
                lastdir = sl[0]
            else:
                print ".",
            anybad = False
            for l in self.execute("cd %s; /home/ubuntu/cptac-galaxy/cptacdcc/cksum.sh -V -f %s %s"%(rdir,l,sl[0]),output=True):
                if 'Checking ' in l:
                    continue
                if 'All checksums match!' in l:
                    continue
                anybad = True
                print "\n"+l
        if not anybad:
            print "\nAll checksums match!"
        self.ssh_session_end()

    def organize_job_results(self,jobid):
        rdir = self.jobdir(jobid) + "/results"
        self.ssh_session_start()
        for l in self.execute("cd %s; /home/ubuntu/cptac-galaxy/organize1all.sh %s *"%(rdir,jobid),output=True):
            print l
        destdir = self.datadir + "/" + jobid
        self.execute("mkdir -p %s"%(destdir,))
        self.execute("cd %s; mv -f mzML PSM.tsv mzIdentML SummaryReports %s"%(rdir,destdir))
        self.ssh_session_end()

    def upload_data(self,fromdir,destname):
        fromdir = fromdir.rstrip('/')
	assert(os.path.isdir(fromdir))
        assert not re.search(r'[^a-zA-Z0-9_.-]',destname)
	destdir = self.datadir + "/" + destname 
        self.ssh_session_start()
        self.execute("mkdir -p %s/%s"%(self.datadir,destname))
        self.ssh_session_end()
	self.rsyncup(fromdir,destdir)

    def download_data(self,destdir,dataname,datatag):
        ddir = self.datadir + "/" + dataname + "/" + datatag;
        assert(os.path.isdir(destdir))
	todir = destdir+"/"+datatag
	if not os.path.isdir(todir):
	    os.makedirs(todir)
        self.rsync(ddir,todir)

    def datanames(self):
	self.ssh_session_start()
        studies = []
        for l in self.execute("ls -1 " + self.datadir,output=True):
	     studies.append(l.strip())
        self.ssh_session_end()
	return sorted(studies)

    def dirnames(self,datatag):
        self.ssh_session_start()
        subdirs = []
        for l in self.execute("ls -1 " + self.datadir + "/" + datatag,output=True):
	     subdirs.append(l.strip())
        self.ssh_session_end()
	return sorted(subdirs)

    def data_manifest(self,base,dir):
	self.ssh_session_start()
	samples = []
	for l in self.execute("ls -1 " + self.datadir + "/" + base + "/" + dir,output=True):
	    if l.endswith('.cksum'):
		print "\t".join([l[:-6],"local",self.datadir + "/" + base + "/" + dir + "/" + l])
        self.ssh_session_end()

    def status_job(self,jobid):
        try:
            self.ssh_session_start()
            for line in self.execute("tail -n 30 -f %s/execute.log"%(self.jobdir(jobid),),output=True):
                print >>sys.stderr, line
        except KeyboardInterrupt:
            self.execute("ps -ef | fgrep %s/execute.log | fgrep tail | awk '{print \\$2}' | xargs -n 30 kill -9"%(jobid,))
        finally:
            self.ssh_session_end()

    def running_jobs(self,needsession=True):
        running = set()
        try:
            if needsession:
                self.ssh_session_start()
            jobsnames = self.list_jobids(needsession=False)
            pids = set()
            for line in self.execute("cat %s/*/execute.pid"%(self.remotebase,),output=True):
                for w in line.split():
                    pids.add(w)
            for line in self.execute("ps %s"%(" ".join(pids)),output=True):
                for w in line.split():
                    if w in jobsnames:
                        running.add(w)
            return sorted(running)
        finally:
            if needsession:
                self.ssh_session_end()

    def status_all(self):
        try:
            self.ssh_session_start()
            for line in self.execute("tail -n 30 -f %s/*/execute.log"%(self.remotebase,),output=True):
                print >>sys.stderr, line
        except KeyboardInterrupt:
            self.execute("ps -ef | fgrep /execute.log | fgrep tail | awk '{print \\$2}' | xargs -n 30 kill -9")
        finally:
            self.ssh_session_end()

    def remove_job(self,jobid):
        gi = GalaxyInstance(url=self.get('url'),key=self.get('apikey'))
        gi.verify=False
        for h in gi.histories.get_histories(name=jobid):
            gi.histories.delete_history(h.get('id'), purge=True)
        rdir = self.jobdir(jobid)
        self.ssh_session_start()
        self.execute("( sh %s/stop.sh; rm -rf %s )"%(rdir,rdir))
        self.ssh_session_end()

    def remove_all_jobs(self):
        for jobid in self.list_jobids():
            self.remove_job(jobid)

class ClusterManager(object):
    iniFile = ".galaxy.ini"

    def __init__(self):
	self.scriptdir = os.path.split(os.path.abspath(sys.argv[0]))[0]
        self.iniFileGeneral = os.path.join(self.scriptdir,self.iniFile)
        self.load()
            
    def load(self):
        lock = lockfile.FileLock(self.iniFile)
        self.config = ConfigParser.SafeConfigParser()
        try:
            lock.acquire()
            found = self.config.read([self.iniFileGeneral,self.iniFile])
        finally:
            lock.release()
        assert found > 0, "Can't find %s file(s)"%(self.iniFile,)
        assert self.config.has_section('GENERAL')

    def add(self,cluster):
        lock = lockfile.FileLock(self.iniFile)
        config = ConfigParser.SafeConfigParser()
        try:
            lock.acquire()
            config.read([self.iniFile])
            name = cluster.get('name')
            assert name
            config.add_section(name)
            for key,value in cluster.items():
                config.set(name,key,value)
            wh = open(self.iniFile,'w')
            config.write(wh)
            wh.close()
        finally:
            lock.release()
        self.load()

    def remove(self,cluster):
        lock = lockfile.FileLock(self.iniFile)
        config = ConfigParser.SafeConfigParser()
        try:
            lock.acquire()
            config.read([self.iniFile])
            name = cluster.get('name')
            assert name
            config.remove_section(name)
            wh = open(self.iniFile,'w')
            config.write(wh)
            wh.close()
        finally:
            lock.release()

    def get(self,key,default=None):
	if self.config.has_option('GENERAL',key):
	    return self.config.get('GENERAL',key)
	return default

    def has(self,key):
	return self.config.has_option('GENERAL',key)

    def items(self):
        return self.config.items('GENERAL')

    def newcluster(self,name,type="Cloudman"):
        d = dict(name=name)
        if type:
            d['type'] = type
        return Cluster(**d)

    def getdefaultcluster(self,type="Cloudman"):
	names = self.getclusternames(type=type)
	if len(names) == 1:
	    return self.getcluster(names[0])
	return None

    def getcluster(self,name,type="Cloudman"):
	if not self.config.has_section(name):
	    return None
	if type and (not self.config.has_option(name,'Type') or self.config.get(name,'Type') != type):
	    return None
        kwargs = dict(self.config.items(name))
	kwargs.update(dict(self.config.items('GENERAL')))
        kwargs['_scriptdir'] = self.scriptdir
	return Cluster(**kwargs)

    def getclusternames(self,type="Cloudman"):
        names = []
        for sec in self.config.sections():
            if type and (not self.config.has_option(sec,'Type') or self.config.get(sec,'Type') != type): 
                continue
	    if sec == 'GENERAL':
		continue
            names.append(sec)
        return names

    def parse_cluster_arg(self,name=None,type="Cloudman"):
        if name:
            cluster = self.getcluster(name,type=type)
        else:
            cluster = self.getdefaultcluster(type=type)
        if not cluster:
            if name:
                print >>sys.stderr, "Cluster \"%s\" not found.\n"%(name,)
            print >>sys.stderr, "Clusters:"
            for sec in self.getclusternames(type=type):
                print >>sys.stderr, " ",sec
            sys.exit(1)
	return cluster

