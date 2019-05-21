#!bin/python

import sys, glob

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning, InsecurePlatformWarning, SNIMissingWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(SNIMissingWarning)

from bioblend.galaxy import GalaxyInstance
gi = GalaxyInstance(url=sys.argv[1],key=sys.argv[2])
gi.verify=False
for wffile in glob.glob(sys.argv[3]):
  print "Workflow:",wffile
  wfi = gi.workflows.import_workflow_from_local_path(wffile)
  wfid = wfi['id']
  name = wfi['name']
  tostrip = ' (imported from API)'
  if name.endswith(tostrip):
    name = name[:-len(tostrip)]
    gi.workflows.rename_workflow(wfid,name)
    wfi = gi.workflows.get_workflows(workflow_id=wfid)[0]
  print "Imported workflow: %s"%(wfi['name'],)
