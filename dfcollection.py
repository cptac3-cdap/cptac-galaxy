#!bin/python

import sys, os, os.path, urllib.request, urllib.parse, urllib.error, tempfile, shutil, time, re, copy
from collections import defaultdict
from subprocess import Popen

import ssl
noverify = ssl._create_unverified_context()

class DatafileCollection(object):
    scriptdirs = [ "cptacdcc",
                   os.path.join("cptac-galaxy","cptacdcc"),
                   os.path.join(os.sep,"home","ubuntu","cptac-galaxy","cptacdcc"), # absolute path
                   os.path.join("..","lib","cptac3-cdap","cptac-dcc","cptacdcc") ]
    resources = ["portal","portalurl","url","dcc","dcctr","s3","local","rclone","pdc","pdcdev","panorama"]

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

        found = False
        for sd in self.scriptdirs:
            if not sd.startswith(os.sep):
                sdfp = os.path.join(self.moduledir,sd)
            else:
                sdfp = sd
            for extn in (".py",".sh",""):
                sp = os.path.join(sdfp,"cptacportal"+extn)
                if os.path.exists(sp):
                    found = True
                    break
            if found:
                break
        if not found:
            print("moduledir = %s"%(self.moduledir,))
            print("scriptdirs = %s"%(self.scriptdirs,))
        assert found, "Can't find cptacportal script..."
        self.cptacportal = sp
        self.s3 = os.path.join(os.path.split(sp)[0],"rclone","s3.sh")
        self.rclone = os.path.join(os.path.split(sp)[0],"rclone","rclone.sh")
        self.credentials = credentials

    def __iter__(self):
        return next(self)

    def __next__(self):
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
        if isinstance(infile,str):
            infiledir = os.path.split(infile)[0]
            infile = open(infile)
            close = True

        for l in infile:
            if not l.strip():
                continue
            if l.startswith('#'):
                continue
            sl = list(map(str.strip,l.rstrip().split('\t')))
            if sl[0].split('/')[0] not in self.resources:
                folder = sl.pop(0)
            else:
                folder = '.'
            resource=sl[0]
            cksumfile=sl[1]
            if infiledir and not os.path.exists(cksumfile):
                if os.path.exists(os.path.join(infiledir,cksumfile)):
                    cksumfile = os.path.join(infiledir,cksumfile)
            extraparams=(sl[2] if len(sl) > 2 else None)
            if outdir != '.':
                folder = os.path.join(outdir,folder)
            self.add(resource,cksumfile,extraparams=extraparams,outdir=folder,position=position)

        if close:
            infile.close()

    def writelist(self,outfile,position=1):
        close = False
        if isinstance(outfile,str):
            outfile = open(outfile,'rw')
            close = True

        for b in sorted(self._files):
            print("\t".join(map(self._files[b][position].get,"resource md5hash sha1hash sizehash filepath".split())), file=outfile)

        if close:
            outfile.close()

    def addstr(self,s,outdir='.'):

        extraparams = None
        spls = list(map(str.strip,s.split(':')))

        if len(spls) == 2:
            resource,cksumfile = spls
        elif len(spls) == 3:
            resource,cksumfile,extraparams = spls
        elif lns(spls) == 4:
            folder,resource,cksumfile,extraparams = spls
        else:
            raise RuntimeError("can't parse --data argument")

        self.add(resource,cksumfile,extraparams,outdir)

    def add(self,resource,cksumdata,extraparams=None,outdir='.',position=1):

        params = {}
        if extraparams != None:
            splparams = re.split(r';([a-z]+)=',';'+extraparams.strip())
            if len(splparams) == 1:
                params['prefixpath'] = extraparams.strip()
            else:
                for i in range(1,len(splparams),2):
                    params[splparams[i]] = splparams[i+1].strip()

        prefixpath = None
        if params.get('prefixpath'):
            prefixpath = params['prefixpath']
        fullpathfmt = None
        if params.get('fullpathfmt'):
            fullpathfmt = params.get('fullpathfmt')
        filenameregex = None
        if params.get('filenameextn'):
            filenameregex = '\.'+re.escape(params['filenameextn'])+'$'
        if params.get('filenameregex'):
            filenameregex = params['filenameregex']
        if filenameregex != None:
            filenameregex = re.compile(filenameregex)
        cksumfmt = "DCC"
        if params.get('cksumfmt'):
            cksumfmt = params['cksumfmt']

        if not cksumdata.endswith(".cksum"):
            raise RuntimeError("Bad checksum file path: %s"%(cksumdata,))

        tmpdir = None
        username = ""
        h = None

        if os.path.exists(cksumdata) and resource != 'local':
            if not fullpathfmt and not prefixpath:
                raise RuntimeError("Prefix path or full path format required for file-based cksum file.")

            h = open(cksumdata,'rb')
            if resource.startswith('dcc/'):
                resource,username = resource.split('/',1)
            elif resource.startswith('dcctr/'):
                resource,username = resource.split('/',1)
            elif resource.startswith('panorama/'):
                resource,username = resource.split('/',1)
            elif resource.startswith('rclone/'):
                resource,remote = resource.split('/',1)
            elif resource == 'rclone' and prefixpath != None and ':' in prefixpath:
                remote,prefixpath = prefixpath.split(':',1)
            elif resource == 'rclone' and fullpathfmt != None and ':' in fullpathfmt:
                remote,fullpathfmt = fullpathfmt.split(':',1)

        else:

            if cksumdata.split(':',1)[0] in ('http','https','ftp'):
                h = urllib.request.urlopen(cksumdata,context=noverify)
                if h.getcode() != 200:
                    RuntimeError("[%s] Can't retrieve URL %s"%(resource,cksumdata))
                if not prefixpath and not fullpathfmt:
                    prefixpath = cksumdata[:-len('.cksum')]

            elif resource in ('portal','portalurl'):
                h = urllib.request.urlopen('https://cptc-xfer.uis.georgetown.edu/publicData/'+cksumdata,context=noverify)
                if h.getcode() != 200:
                    RuntimeError("[%s] Can't retrieve CPTAC Data Portal path %s"%(resource,cksumdata))
                if not prefixpath and not fullpathfmt:
                    if resource == 'portal':
                        prefixpath = cksumdata[:-len('.cksum')]
                    else:
                        prefixpath = 'https://cptc-xfer.uis.georgetown.edu/publicData/'+cksumdata[:-len('.cksum')]

            elif resource in ('s3',):
                tmpdir = tempfile.mkdtemp(suffix="",prefix=".",dir=os.getcwd())
                cmd = "\"%s\" \"%s\""%(self.s3,cksumdata)
                proc = Popen(cmd,cwd=tmpdir,shell=True)
                proc.wait()
                cksumdatafile = os.path.join(tmpdir,cksumdata.rsplit('/',1)[1])
                if not os.path.exists(cksumdatafile):
                    raise RuntimeError("[%s] Can't retrieve S3 path %s"%(resource,cksumdata))
                h = open(cksumdatafile,'rb')
                if not prefixpath and not fullpathfmt:
                    prefixpath = cksumdata[:-len('.cksum')]

            elif resource.split('/')[0] == "rclone":
                if '/' in resource:
                    resource,remote = resource.split('/',1)
                elif ":" in cksumdata:
                    remote,cksumdata = cksumdata.split(":",1)
                tmpdir = tempfile.mkdtemp(suffix="",prefix=".",dir=os.getcwd())
                cmd = "\"%s\" \"%s\" \"%s\""%(self.rclone,remote,cksumdata)
                proc = Popen(cmd,cwd=tmpdir,shell=True)
                proc.wait()
                cksumdatafile = os.path.join(tmpdir,cksumdata.rsplit('/',1)[1])
                if not os.path.exists(cksumdatafile):
                    raise RuntimeError("[%s] Can't retrieve path %s:%s"%("rclone",remote,cksumdata))
                h = open(cksumdatafile,'rb')
                if not prefixpath and not fullpathfmt:
                    prefixpath = cksumdata[:-len('.cksum')]

            elif resource in ('local','pdc','pdcdev','panorama'):
                if not os.path.exists(cksumdata):
                    raise RuntimeError("[%s] Can't retrieve local path %s"%(resource,cksumdata))
                h = open(cksumdata,'rb')
                if not prefixpath and not fullpathfmt:
                    prefixpath = cksumdata[:-len('.cksum')]

            elif resource.startswith('dcc'):
                if self._dccreqcount > 0 and self._dccreqcount % self._dccreqwaitfreq == 0:
                    time.sleep(self._dccreqwait)
                self._dccreqcount += 1
                try:
                    resource,username = resource.split('/')
                    credkey = "%s@%s"%(username,resource)
                except ValueError:
                    if self.credentials:
                        forresource = [ v for v in self.credentials.values() if v['site'] == resource ]
                        assert len(forresource == 1)
                        username = forresource[0]['username']
                        credkey = "%s@%s"%(username,resource)
                tmpdir = tempfile.mkdtemp(suffix="",prefix=".",dir=os.getcwd())
                credfile = None
                if resource == "dcc":
                    theportaltag = "dccnodescrape"
                    if self.credentials and credkey in self.credentials:
                        credfile = os.path.join(tmpdir,'cptacdcc.ini')
                elif resource == "dcctr":
                    theportaltag = "transfer"
                    if self.credentials and credkey in self.credentials:
                        credfile = os.path.join(tmpdir,'cptactransfer.ini')
                if credfile:
                    wh = open(credfile,'w')
                    print("""
[Aspera]
Docker = True
[Portal]
User = %s
Password = %s
                    """%(username,self.credentials[credkey]['password'].replace('%','%%')), file=wh)
                    wh.close()
                cmd = "%s %s get -q %s"%(self.cptacportal,theportaltag,cksumdata)
                cksumdatafile = os.path.join(tmpdir,cksumdata.rsplit('/',1)[1])
                maxattempts = 5
                attempt = 0
                env = copy.copy(os.environ)
                env['NONINTERACTIVE'] = "1"
                while attempt < maxattempts:
                    attempt += 1
                    proc = Popen(cmd,cwd=tmpdir,shell=True,env=env)
                    proc.wait()
                    if proc.returncode == 0 and os.path.exists(cksumdatafile):
                        break
                    time.sleep(10)
                if proc.returncode != 0 or not os.path.exists(cksumdatafile):
                    raise RuntimeError("[%s] Can't retrieve CPTAC DCC path %s"%(resource,cksumdata))
                h = open(cksumdatafile,'rb')
                if not prefixpath and not fullpathfmt:
                    prefixpath = cksumdata[:-len('.cksum')]
                if credfile:
                    os.unlink(credfile)

        if not h:
            raise RuntimeError("[%s] Bad file handle for %s"%(resource,cksumdata))

        if fullpathfmt == None:
            assert(prefixpath)
            fullpathfmt = prefixpath + '/%s'

        for l in map(bytes.decode,h):
            sline = []
            if cksumfmt == "DCC":
                sline = list(map(str.strip,l.rstrip().split('\t',3)))
            elif cksumfmt == "sha1sum":
                sline = list(map(str.strip,l.split()))
                sline = ["",sline[0],"",sline[1].lstrip("*")]
            elif cksumfmt == "md5sum":
                sline = list(map(str.strip,l.split()))
                sline = [sline[0],"","",sline[1].lstrip("*")]

            if len(sline) != 4:
                raise RuntimeError("Bad format for cksum file %s"%(cksumdata,))
            if filenameregex != None and not filenameregex.search(sline[3]):
                continue
            sline[3] = fullpathfmt%(sline[3],)
            if resource == "rclone":
                sline[3] = remote+":"+sline[3]
            if resource == "url":
                dirname,filename = sline[3].split('?')[0].rsplit('/',1)
            else:
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

        h.close()
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)

if __name__ == '__main__':

    import sys, os
    dfc = DatafileCollection()
    dfc.read(*sys.argv[1:])
    for i in range(1,len(sys.argv)):
        dfc.writelist(sys.stdout,position=i)
