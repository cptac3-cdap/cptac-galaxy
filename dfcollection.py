#!bin/python

import sys, os, os.path, urllib, tempfile, shutil, time, re
from collections import defaultdict
from subprocess import Popen

class DatafileCollection(object):
    scriptdirs = [ "cptacdcc", os.path.join("..","lib","cptacdcc") ]
    resources = ["portal","portalurl","url","dcc","dcctr","s3","local"]

    def __init__(self,credentials=None):
	self._files = defaultdict(dict)
	self._positions = set()
	self._dccreqcount = 0
	self._dccreqwaitfreq = 5
	self._dccreqwait = 20

	try:
            self.moduledir = os.path.split(os.path.abspath(__file__))[0]
	except:
	    self.moduledir = os.path.split(os.path.abspath(sys.argv[0]))[0]
	if os.path.isfile(self.moduledir) or self.moduledir.endswith('.zip'):
	    # Probably in a cx_Freeze setup...
	    self.moduledir = os.path.split(self.moduledir)[0]
	    self.moduledir = os.path.split(self.moduledir)[0]

	found = False
	for sd in self.scriptdirs:
   	    sdfp = os.path.join(self.moduledir,sd)
	    for extn in (".py",".sh",""):
		sp = os.path.join(sdfp,"cptacportal"+extn)
		if os.path.exists(sp):
		     found = True
		     break
	    if found:
		break
        self.cptacportal = sp
	self.s3 = os.path.join(os.path.split(sp)[0],"rclone","s3.sh")
	self.credentials = credentials

    def __iter__(self):
	return self.next()

    def next(self):
	for b in sorted(self._files):
	    yield self._files[b][1]

    def keys(self):
	return sorted(self._files)

    def positions(self):
	return sorted(self._positions)

    def __getitem__(self,b):
	return self._files[b]

    def __contains__(self,b):
	return (b in self._files)

    @staticmethod
    def dssplit(name):
        if '.' not in name:
            return (name,'')
        m = re.search(r'^(.*)-(\d+\.\d+\..*)$',name)
	if m:
	    ext=m.group(2)
	    base=m.group(1)
	    return base,ext
        return name.split('.',1)

    def read(self,*args,**kwargs):
	outdir = kwargs.get('outdir','.')
	for i,f in enumerate(args):
	    self._read(f,outdir,i+1)

    def _read(self,infile,outdir,position):
        
        infiledir = None
	close = False
	if isinstance(infile,basestring):
	    infiledir = os.path.split(infile)[0]
	    infile = open(infile,'r')
	    close = True

        for l in infile:
            if not l.strip():
                continue
            if l.startswith('#'):
                continue
            sl = map(str.strip,l.rstrip().split('\t'))
            if sl[0].split('/')[0] not in self.resources:
                folder = sl.pop(0)
            else:
                folder = '.'
            resource=sl[0]
            cksumfile=sl[1]
            if infiledir and not os.path.exists(cksumfile):
		if os.path.exists(os.path.join(infiledir,cksumfile)):                                         
                     cksumfile = os.path.join(infiledir,cksumfile)
            fileroot=(sl[2] if len(sl) > 2 else None)
            if outdir != '.':
                folder = os.path.join(outdir,folder)
            self.add(resource,cksumfile,prefixpath=fileroot,outdir=folder,position=position)
	
	if close:
	    infile.close()

    def writelist(self,outfile,position=1):
        close = False
        if isinstance(outfile,basestring):
            outfile = open(outfile,'rw')
            close = True

	for b in sorted(self._files):
	    print >>outfile, "\t".join(map(self._files[b][position].get,"resource md5hash sha1hash sizehash filepath".split()))

        if close:
            outfile.close()

    def addstr(self,s,outdir='.'):

        fileroot = None
        spls = map(str.strip,s.split(':'))

        if len(spls) == 2:
            resource,cksumfile = spls
        elif len(spls) == 3:
            resource,cksumfile,fileroot = spls
        elif lns(spls) == 4:
            folder,resource,cksumfile,fileroot = spls
        else:
            raise RuntimeError("can't parse --data argument")

        self.add(resource,cksumfile,fileroot,outdir)
              
    def add(self,resource,cksumdata,prefixpath=None,outdir='.',position=1):

        if not cksumdata.endswith(".cksum"):
            raise RuntimeError("Bad checksum file path: %s"%(cksumdata,))

        tmpdir = None
	username = ""
        h = None

        if os.path.exists(cksumdata) and resource != 'local':
	    if not prefixpath:
                raise RuntimeError("Prefix path required for file-based cksum file.")

            h = open(cksumdata)
	    if resource.startswith('dcc'):
	        resource,username = resource.split('/')

        else:

            if cksumdata.split(':',1)[0] in ('http','https','ftp'):
                h = urllib.urlopen(cksumdata)
                if h.getcode() != 200:
                    RuntimeError("[%s] Can't retrieve URL %s"%(resource,cksumdata))
                if not prefixpath:
                    prefixpath = cksumdata[:-len('.cksum')]

            elif resource in ('portal','portalurl'):
                h = urllib.urlopen('https://cptc-xfer.uis.georgetown.edu/publicData/'+cksumdata)
                if h.getcode() != 200:
                    RuntimeError("[%s] Can't retrieve CPTAC Data Portal path %s"%(resource,cksumdata))
                if not prefixpath:
                    if resource == 'portal':
                        prefixpath = cksumdata[:-len('.cksum')]
                    else:
                        prefixpath = 'https://cptc-xfer.uis.georgetown.edu/publicData/'+cksumdata[:-len('.cksum')]

	    elif resource in ('s3',):
                tmpdir = tempfile.mkdtemp(suffix="",prefix=".",dir=os.getcwd())
                cmd = "%s %s"%(self.s3,cksumdata)
                proc = Popen(cmd,cwd=tmpdir,shell=True)
                proc.wait()
                cksumdatafile = os.path.join(tmpdir,cksumdata.rsplit('/',1)[1])
                if not os.path.exists(cksumdatafile):
                    raise RuntimeError("[%s] Can't retrieve S3 path %s"%(resource,cksumdata))
                h = open(cksumdatafile)
                if not prefixpath:
                    prefixpath = cksumdata[:-len('.cksum')]

	    elif resource in ('local',):
                if not os.path.exists(cksumdata):
                    raise RuntimeError("[%s] Can't retrieve local path %s"%(resource,cksumdata))
		h = open(cksumdata)
                if not prefixpath:
                    prefixpath = cksumdata[:-len('.cksum')]

            elif resource.startswith('dcc'):
		if self._dccreqcount > 0 and self._dccreqcount % self._dccreqwaitfreq == 0:
                    time.sleep(self._dccreqwait)
		self._dccreqcount += 1
		resource,username = resource.split('/')
                tmpdir = tempfile.mkdtemp(suffix="",prefix=".",dir=os.getcwd())
		credfile = None
                if resource == "dcc":
                    theportaltag = "dccnodescrape"
		    if self.credentials and username in self.credentials and not self.credentials[username]['transfer']:
		        credfile = os.path.join(tmpdir,'cptacdcc.ini')
		else:
                    theportaltag = "transfer"
		    if self.credentials and username in self.credentials and self.credentials[username]['transfer']:
		        credfile = os.path.join(tmpdir,'cptactransfer.ini')
		if credfile:
		    wh = open(credfile,'w')
		    print >>wh, """
[Portal]
User = %s
Password = %s
		    """%(username,self.credentials[username]['password'].replace('%','%%'))
                    wh.close()
                cmd = "%s %s get -q %s"%(self.cptacportal,theportaltag,cksumdata)
                cksumdatafile = os.path.join(tmpdir,cksumdata.rsplit('/',1)[1])
                maxattempts = 5
                attempt = 0
                while attempt < maxattempts:
                    attempt += 1
                    proc = Popen(cmd,cwd=tmpdir,shell=True)
		    proc.wait()
                    if proc.returncode == 0 and os.path.exists(cksumdatafile):
                        break
                    time.sleep(10)
                if proc.returncode != 0 or not os.path.exists(cksumdatafile):
                    raise RuntimeError("[%s] Can't retrieve CPTAC DCC path %s"%(resource,cksumdata))
                h = open(cksumdatafile)
                if not prefixpath:
                    prefixpath = cksumdata[:-len('.cksum')]
		if credfile:
		    os.unlink(credfile)

        if not h:
            raise RuntimeError("[%s] Bad file handle for %s"%(resource,cksumdata))

        for l in h:
            sline = l.rstrip().split('\t',3)
	    if len(sline) != 4:
		raise RuntimeError("Bad format for cksum file %s"%(cksumdata,))
            sline[3] = prefixpath + '/' + sline[3]
            dirname,filename = sline[3].rsplit('/',1)
            basename,fileext = self.dssplit(filename)
	    self._positions.add(position)
            self._files[basename][position] = \
		dict(md5hash=sline[0],
                     sha1hash=sline[1],
                     sizehash=sline[2],
                     basename=basename,
                     extension=fileext,
                     filepath=sline[3],
                     filename=filename,
                     dirname=dirname,
                     resource=resource,
		     username=username,
                     results=outdir)

        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)

if __name__ == '__main__':
    
    import sys, os
    dfc = DatafileCollection()
    dfc.read(*sys.argv[1:])
    for i in range(1,len(sys.argv)):
        dfc.writelist(sys.stdout,position=i)

