


import json, re, copy, csv, os, os.path, sys
from collections import defaultdict

import requests

try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    pass

try:
    from requests.packages.urllib3.exceptions import InsecurePlatformWarning
    requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
except ImportError:
    pass

try:
    from requests.packages.urllib3.exceptions import SNIMissingWarning
    requests.packages.urllib3.disable_warnings(SNIMissingWarning)
except ImportError:
    pass

import urllib.request, urllib.parse, urllib.error

class PDC(object):
    resource = "pdc"
    graphql = 'https://pdc.cancer.gov/graphql'
    # graphql = 'https://proteomic.datacommons.cancer.gov/graphql'
    def __init__(self):
        pass

    @staticmethod
    def rawfilesortkey(f):
        try:
            pdind = (int(f.get('plex_or_dataset_name_index',"")),"")
        except ValueError:
            pdind = (1e+20,f.get('plex_or_dataset_name_index'))
        try:
            fn = (int(f['fraction_number']),"")
        except ValueError:
            fn = (1e+20,f['fraction_number'])
        return pdind[0],pdind[1],f['plex_or_dataset_name'],fn[0],fn[1]

    def post(self,query):
        return requests.post(self.graphql, json={'query': query}, verify=False)

    def query(self,query):

        pdc_response = self.post(query)

        # Set up a data structure for the query result
        decoded = dict()

        # Check the results
        if pdc_response.ok:
            # Decode the response
            decoded = pdc_response.json()
            # print(decoded)
        else:
            # Response not OK, see error
            try:
                decoded = pdc_response.json()
                if 'errors' in decoded:
                    msg = []
                    for e in decoded['errors']:
                        msg.append(e['message'])
                    msg = "\n".join(msg)
                    raise RuntimeError(msg)
            except (ValueError,TypeError):
                pdc_response.raise_for_status()

        return decoded

    _study_query = '''
    { study (%s, acceptDUA: true) {
    study_id study_submitter_id program_id project_id study_name
    program_name project_name disease_type primary_site
    analytical_fraction experiment_type cases_count aliquots_count
    filesCount { data_category file_type files_count }
    } }
    '''
    def _study(self,**kw):
        constraints = []
        for k in kw:
            constraints.append("%s: \"%s\""%(k,kw[k]))
        constraints = ", ".join(constraints)
        res =  self.query(self._study_query%(constraints,))
        if res['data']['study']:
            for r in res['data']['study']:
                yield r

    def find_study_id(self,search_term):
        study_id = None
        for i,r in enumerate(self._filesCountPerStudy(study_submitter_id=search_term)):
            if study_id != None and r['study_id'] != study_id:
                raise RuntimeError("Mutiple studies match: %s"%(search_term,))
            study_id = r['study_id']
        for i,r in enumerate(self._filesCountPerStudy(pdc_study_id=search_term)):
            if study_id != None and r['study_id'] != study_id:
                raise RuntimeError("Mutiple studies match: %s"%(search_term))
            study_id = r['study_id']
        if not study_id:
            raise RuntimeError("No studies match: %s"%(search_term))
        return study_id

    def find_study(self,study,**kwargs):
        studydict = self.get_study(study)
        if studydict:
            stid = studydict['study_id']
        else:
            stid = self.find_study_id(study)
        return Study(self,stid,**kwargs)

    def get_study(self,study_id):
        for r in self._study(study_id=study_id):
            return r

    _filesPerStudy_query = '''
    { filesPerStudy(%s, acceptDUA: true) {
        file_id file_submitter_id file_name study_name study_submitter_id
        study_id file_type file_location md5sum file_size data_category
        file_format signedUrl { url }
    } }
    '''
    def _filesPerStudy(self,limit=None,fnmatch=None,**kw):
        constraints = []
        for k in kw:
            constraints.append("%s: \"%s\""%(k,kw[k]))
        constraints = ", ".join(constraints)
        for i,r in enumerate(self.query(self._filesPerStudy_query%(constraints,))['data']['filesPerStudy']):
            # if '_CompRef_' in r['file_name']:
            #     continue
            if not fnmatch or re.search(fnmatch,r['file_name'].rsplit('.',1)[0]):
                r['signedUrl'] = r['signedUrl']['url']
                yield r
                if limit != None and i > limit:
                    break

    def _rawfilesPerStudy(self,study_id,limit=None,fnmatch=None,**kw):
        total = self._rawfilesCountPerStudy(study_id)
        i = 0
        for st in range(0,total,1000):
          for r in self._getPaginatedFiles(offset=st,limit=1000,study_id=study_id,data_category="Raw Mass Spectra",**kw):
            if not fnmatch or re.search(fnmatch,r['file_name'].rsplit('.',1)[0]):
              # r['signedUrl'] = r['signedUrl']['url']
              yield r
              i += 1
              if limit != None and i >= limit:
                break

    def _mdfilesPerStudy(self,study_id,**kw):
        total = self._mdfilesCountPerStudy(study_id)
        for st in range(0,total,1000):
          for r in self._getPaginatedFiles(offset=st,limit=1000,study_id=study_id,data_category="Other Metadata",**kw):
            if r['file_name'].endswith('.txt') and r['file_type'] == 'Text' and r['file_format'] == 'TSV':
              yield r

    _filesCountPerStudy_query = '''
    { filesCountPerStudy (%s, acceptDUA: true) {
        study_id pdc_study_id study_submitter_id file_type files_count data_category}
    }
    '''

    def _filesCountPerStudy(self,data_category=None,**kw):
        constraints = []
        for k in kw:
            constraints.append("%s: \"%s\""%(k,kw[k]))
        constraints = ", ".join(constraints)
        for r in self.query(self._filesCountPerStudy_query%(constraints,))['data']['filesCountPerStudy']:
            if not data_category or r['data_category'] == data_category:
                yield r

    def _rawfilesCountPerStudy(self,study_id,**kw):
        for r in self._filesCountPerStudy(study_id=study_id,data_category="Raw Mass Spectra",**kw):
            return r['files_count']
        return None

    def _mdfilesCountPerStudy(self,study_id,**kw):
        for r in self._filesCountPerStudy(study_id=study_id,data_category="Other Metadata",**kw):
            return r['files_count']
        return None

    _getPaginatedFiles_query = '''
       { getPaginatedFiles(offset: %s, limit: %s, %s, acceptDUA: true) { 
         total 
         files { 
           study_id pdc_study_id study_submitter_id file_id file_name file_type md5sum data_category
         }  
         pagination { 
          count sort from page total pages size
         }
       }}
    '''
        
    def _getPaginatedFiles(self,offset=0,limit=10,**kw):
        constraints = []
        for k in kw:
            constraints.append("%s: \"%s\""%(k,kw[k]))
        constraints = ", ".join(constraints)
        for r in self.query(self._getPaginatedFiles_query%(offset,limit,constraints,))['data']['getPaginatedFiles']['files']:
            yield r

    def study_rawfiles(self,study_id,limit=None,fnmatch=None,ansampregex=None,ansampregexgrp=None):
        biospec = {}
        for r in self._biospecimenPerStudy(study_id):
            biospec[r['aliquot_id']] = copy.copy(r)
        expdes = {}
        for r in self._studyExperimentalDesign(study_id):
            expdes[r['plex_dataset_name']] = copy.copy(r)
        # print expdes.keys()
        if ansampregex:
            ansampregex = re.compile(ansampregex)
        for f in self._rawfilesPerStudy(study_id,limit=limit,fnmatch=fnmatch):
            fid = f['file_id']
            f.update(self._fileMetadata(file_id=fid))
            for a in f['aliquots']:
                a.update(biospec.get(a['aliquot_id'],{}))
            f.update(expdes[f['plex_or_dataset_name']])
            if ansampregex:
                m = ansampregex.search(f['plex_or_dataset_name'])
                if m:
                    if not ansampregexgrp and m.group(0):
                        f['plex_or_dataset_name_index'] = m.group(0)
                    elif ansampregexgrp and m.group(ansampregexgrp):
                        f['plex_or_dataset_name_index'] = m.group(ansampregexgrp)
            yield f

    def study_experimental_design(self,study_id):
        for f in self._mdfilesPerStudy(study_id):
            if f['file_name'].endswith('.sample.txt'):
                return f

    def study_label_batches(self,study_id,names):
        for f in self._mdfilesPerStudy(study_id):
            if f['file_name'].rsplit('.',1)[0] in names:
                yield f

    def study_files(self,study_id):
        for f in self._filesPerStudy(study_id=study_id):
            yield f

    _fileMetadata_query = '''
    { fileMetadata(file_id: "%(file_id)s", acceptDUA: true) {
    file_submitter_id file_name file_size md5sum plex_or_dataset_name
    analyte instrument file_location file_submitter_id fraction_number
    experiment_type aliquots { aliquot_id aliquot_submitter_id
    sample_id sample_submitter_id } } }
    '''
    def _fileMetadata(self,file_id):
        for r in self.query(self._fileMetadata_query%dict(file_id=file_id))['data']['fileMetadata']:
            return r

    _biospecimenPerStudy_query = '''
    { biospecimenPerStudy(study_id: "%(study_id)s", acceptDUA: true) {
    aliquot_id sample_id case_id aliquot_submitter_id
    sample_submitter_id case_submitter_id aliquot_status case_status
    sample_status project_name sample_type disease_type primary_site pool taxon aliquot_is_ref
    } }
    '''
    def _biospecimenPerStudy(self,study_id):
        for r in self.query(self._biospecimenPerStudy_query%dict(study_id=study_id))['data']['biospecimenPerStudy']:
            yield r

    _studyExperimentalDesign_query = '''
     { studyExperimentalDesign (study_id: "%(study_id)s", acceptDUA: true) {
     study_run_metadata_id, study_run_metadata_submitter_id, study_id,
     study_submitter_id, analyte, acquisition_type, experiment_type,
     plex_dataset_name, experiment_number, number_of_fractions,
     label_free{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     itraq_113{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     itraq_114{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     itraq_115{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     itraq_116{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     itraq_117{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id},
     itraq_118{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     itraq_119{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     itraq_121{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     tmt_126{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     tmt_127n{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     tmt_127c{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id},
     tmt_128n{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     tmt_128c{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     tmt_129n{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     tmt_129c{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     tmt_130n{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     tmt_130c{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}, 
     tmt_131{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id},
     tmt_131c{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id},
     tmt_132n{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id},
     tmt_132c{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id},
     tmt_133n{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id},
     tmt_133c{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id},
     tmt_134n{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id},
     tmt_134c{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id},
     tmt_135n{aliquot_id, aliquot_run_metadata_id, aliquot_submitter_id}
     } }
    '''
    def _studyExperimentalDesign(self,study_id):
        for r in self.query(self._studyExperimentalDesign_query%dict(study_id=study_id))['data']['studyExperimentalDesign']:
            yield r

class PDCSTAGE(PDC):
    graphql = 'https://pdc-stage.esacinc.com/graphql'
    user = 'pdcuser'
    password = 'PDCsa5t93'

    def post(self,query):
        return requests.post(self.graphql, json={'query': query}, auth=(self.user,self.password), verify=False)

class PDCDEV(PDC):
    resource = "pdcdev"
    graphql = 'https://pdc-dev.esacinc.com/graphql'
    user = 'pdcuser'
    password = 'PDCus3r67'

    def post(self,query):
        return requests.post(self.graphql, json={'query': query}, auth=(self.user,self.password), verify=False)

def labelsort(l):
    m = re.search('^(tmt|itraq)\_(\d+)([nc]?)$',l.lower())
    assert m, "Label \"%s\" doesn't match regular expression"%(l,)
    # print(m.group(1),int(m.group(2)),m.group(3),-1*(m.group(3)=="n")+1*(m.group(3)=="c"))
    return m.group(1),int(m.group(2)),-1*(m.group(3)=="n")+1*(m.group(3)=="c")

class Study(object):

    def __init__(self,pdc,study_id,rawfnmatch=None,ratiodenom=None,labelbatch=None,ansampregex=None,ansampregexgrp=None):
        self._pdc = pdc
        self._study_id = study_id
        self._study = pdc.get_study(study_id)
        self._rawfiles = []
        taxon = set()
        instr = set()
        ansamps = set()
        labels = set()
        pool = defaultdict(int)
        for f in sorted(pdc.study_rawfiles(self._study_id,fnmatch=rawfnmatch,ansampregex=ansampregex,ansampregexgrp=ansampregexgrp),key=PDC.rawfilesortkey):
            for a in f['aliquots']:
                if a.get('taxon') and a.get('aliquot_is_ref') != 'Yes':
                    taxon.add(a.get('taxon'))
                if a.get('aliquot_is_ref') == 'Yes':
                    aid = a.get('aliquot_id')
                    for k in f:
                        if f[k] and (k.startswith('itraq_') or k.startswith('tmt_')):
                            if f[k][0]['aliquot_id'] == aid:
                                pool[k] += 1
                                pool[(aid+":"+k)] += 1
                            labels.add(k)
                    pool[aid] += 1
            instr.add(f['instrument'])
            ansamps.add(f['plex_or_dataset_name'])
            assert f['analyte'] == self._study['analytical_fraction']
            assert f['experiment_type'] == self._study['experiment_type']
            self._rawfiles.append(f)

        assert len(taxon) <= 1
        self._taxon = None
        if len(taxon) == 1:
            self._taxon = taxon.pop()
        assert len(instr) <= 1
        self._instr = None
        if len(instr) == 1:
            self._instr = instr.pop()
        self._batches = []
        self._missing_batches = []
        self._exprdes = {}
        self._has_pool_label = False
        self._has_ratios = False
        self._has_label_reagents = False
        poollabels = set()
        nraw = len(self._rawfiles)
        for k,v in list(pool.items()):
            if v == nraw:
                poollabels.add(k)
        if ratiodenom != None:
            if set(ratiodenom) <= poollabels and set(ratiodenom) <= labels:
                denom = set(ratiodenom)
            else:
                print("Bad ratio denominators chosen, choose from %s."%(", ".join(set(poollabels)&set(labels),)),file=sys.stderr)
                sys.exit(1)
        else:
            denom = (poollabels&labels)
            # assert len(denom) == 1, "Can't determine POOL label..."
        assert len(denom) >= 1, "Can't automatically determine ratio denominators, choose from %s."%(", ".join(set(poollabels)&set(labels),))

        num = (labels-denom)
        ratios = []
        for di in sorted(denom,key=labelsort):
            for ni in sorted(num,key=labelsort):
                ratios.append((ni,di))

        ansamp2labelbatch = {}
        if labelbatch and os.path.exists(labelbatch):
            for l in open(labelbatch,'rt'):
                sl = l.split()
                ansamp2labelbatch[sl[0]] = sl[1]
        else:
            for ansamp in ansamps:
                ansamp2labelbatch[ansamp] = labelbatch

        batchnames = set()
        for ansamp in ansamps:
            self._exprdes[ansamp] = {}
            # How do we determine the label reagent?
            if labelbatch:
                self._exprdes[ansamp]['labelreagent'] = ansamp2labelbatch[ansamp]
                self._has_label_reagents = True
                batchnames.add(labelbatch)
            if len(ratios) > 0:
                self._exprdes[ansamp]['ratios'] = ratios
                self._has_ratios = True
            # if len(denom) == 1 and len(poollabel) == 3:
            if len(denom) == 1:
                self._exprdes[ansamp]['poollabel'] = list(denom)[0]
                self._has_pool_label = True

        self._batches = list(self._pdc.study_label_batches(self._study_id,batchnames))
        for b in self._batches:
            assert b['file_name'].rsplit('.',1)[0] in batchnames
            batchnames.remove(b['file_name'].rsplit('.',1)[0])
        if len(batchnames) > 0:
            self._missing_batches = list(batchnames)

    def name(self):
        return self._study['study_name']

    def id(self):
        return self._study['study_id']

    def submitter_id(self):
        return self._study['study_submitter_id']

    def experiment_type(self):
        return self._study['experiment_type']

    def analytical_fraction(self):
        return self._study['analytical_fraction']

    def instrument(self):
        return self._instr

    def taxon(self):
        return self._taxon

    def files(self):
        return self._pdc.study_files(self._study_id)

    def rawfiles(self):
        return iter(self._rawfiles)

    def write_label_reagents(self,directory):
        for bn in sorted(self._missing_batches):
            print("WARNING: Labeling reagent batch correction file %s.txt not available."%(bn,),file=sys.stderr)
        for f in self._batches:
            fn = f['file_name']
            data=urllib.request.urlopen(f['signedUrl']).read()
            wh = open(os.path.join(directory,fn),'w')
            wh.write(data)
            wh.close()

    def label_reagent(self,analytical_sample):
        assert analytical_sample in self._exprdes
        return self._exprdes[analytical_sample].get('labelreagent')

    def label_reagents(self):
        lr = set()
        for d in list(self._exprdes.values()):
            if d.get('labelreagent'):
                lr.add(d.get('labelreagent'))
        return sorted(lr)

    def ratios(self,analytical_sample):
        assert analytical_sample in self._exprdes
        return self._exprdes[analytical_sample].get('ratios')

    def pool_label(self,analytical_sample):
        assert analytical_sample in self._exprdes, "%s not in %s."%(analytical_sample, ", ".join(sorted(self._exprdes.keys())))
        return self._exprdes[analytical_sample].get('poollabel')

    def has_ratios(self):
        return self._has_ratios

    def has_label_reagents(self):
        return self._has_label_reagents

    def has_pool_label(self):
        return self._has_pool_label

if __name__ == "__main__":

    import sys

    pdc = eval(sys.argv[1])()

    try:
        st = pdc.find_study(sys.argv[2])
        print(st.name())
        print("RAW spectra files")
        for f in st.rawfiles():
            print("",f['file_name'],)
            # print json.dumps(f,indent=2)
        # print "Text files"
        # for f in st.files():
        #     if f['file_name'].endswith('.txt'):
        #         print "",f['file_name']
        # for r in pdc._studyExperimentalDesign(st.id()):
        #     print r

    except RuntimeError as e:
        print(e.args[0])
        sys.exit(1)
