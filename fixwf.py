#!/bin/env python27

import sys
import json
import shutil
wf = json.loads(open(sys.argv[1]).read())

for key in list(wf['steps']):
    if key != int(key):
        wf['steps'][int(key)] = wf['steps'][key]
        del wf['steps'][key]

for key in list(wf['steps']):
    step = wf['steps'][key]
    if step['tool_id'] == "ReAdw4Mascot2_raw_pulsar":
	# Change 1, to deal with additional output file
	pja = step['post_job_actions']
	key = "HideDatasetActionoutput"+str(len(pja))
	pja[key] = dict(action_arguments=[],action_type="HideDatasetAction",output_name="reportersfile")
	step['post_job_actions'] = pja
	# Change 2, set values for advanced.ms1profile and advanced.spsms3
	state = json.loads(step['tool_state'])
	advanced = json.loads(state['advanced'])
	advanced['ms1profile'] = "true"
	advanced['spsms3'] = "false"
	state['advanced'] = json.dumps(advanced)
	step['tool_state'] = json.dumps(state)
	
shutil.move(sys.argv[1],sys.argv[1]+".bak")
wh = open(sys.argv[1],'w')
wh.write(json.dumps(wf,sort_keys=True,indent=4))
wh.close()
