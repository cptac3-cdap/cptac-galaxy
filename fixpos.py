#!/bin/env python3

import json, sys

for f in sys.argv[1:]:
    wfdict = json.loads(open(f).read())
    for key in list(wfdict['steps']):
        wfdict['steps'][int(key)] = wfdict['steps'][key]
        del wfdict['steps'][key]
    for st in wfdict['steps']:
        if 'workflow_outputs' in wfdict['steps'][st]:
            wfdict['steps'][st]['workflow_outputs'] = sorted(wfdict['steps'][st]['workflow_outputs'],key=lambda d: d.get('output_name'))
    for st in wfdict['steps']:
        if 'position' in wfdict['steps'][st]:
            for k,v in wfdict['steps'][st]['position'].items():
                wfdict['steps'][st]['position'][k] = round(v,6)
    wh = open(f,'w')
    wh.write(json.dumps(wfdict,sort_keys=True,indent=4))
    wh.close()
