"""JSONL bridge to a pinned, unmodified jev-ultrafast checkout; no Chrome connection."""
import json, os, sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
os.environ['TYPESAFE_API_KEY']=Path(os.environ.get('TYPESAFE_API_KEY_FILE',str(Path.home()/'.config/jev-benchmark/typesafe-api-key'))).read_text().strip()
from jev_ultrafast.model import choose, field_context, field_text
for line in sys.stdin:
    try:
        req=json.loads(line)
        if req['method']=='choose': result=choose(req['state'],req['goal'],req.get('history',[]))
        elif req['method']=='text':
            value,meta=field_text(field_context(req['goal'],req['action'],req['state'],req.get('history',[])))
            result={'text':value,**meta}
        else: raise ValueError('unknown method')
        print(json.dumps({'ok':True,'result':result}),flush=True)
    except Exception as e:
        # Do not echo provider bodies, API keys or inputs.
        print(json.dumps({'ok':False,'error':type(e).__name__}),flush=True)
