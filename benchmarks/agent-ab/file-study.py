"""Secondary experiment: fresh baseline vs fixed-file adapter; not the stock MCP API."""
import argparse,json,hashlib
from pathlib import Path
import run as b
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--plan-only',action='store_true');args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True,mode=0o700)
trials=[]
for repeat in range(1,4):
 for index,profile in enumerate([b.PROFILES[0],b.PROFILES[2]]):
  for arm in (['baseline','file'] if (index+repeat)%2 else ['file','baseline']):
   trials.append({'id':f'{profile["id"]}-repository-evidence-r{repeat}-{arm}','profile':profile,'workload':'repository-evidence','repeat':repeat,'arm':arm})
plan={'design':'Secondary fixed-file adapter experiment, prompted after primary pilot exposed argument-copying overhead; fresh baselines, sequential counterbalanced order. Not a stock Jev Kit MCP capability. No gold tuning.','timeout_s':180,'fixture_sha256':hashlib.sha256((b.ROOT/'repository-evidence.json').read_bytes()).hexdigest(),'trials':trials}
if (args.out/'plan.json').exists():assert json.loads((args.out/'plan.json').read_text())==plan
else:b.save(args.out/'plan.json',plan)
if args.plan_only:print('Frozen',len(trials),'secondary trials')
else:
 for trial in trials:
  r=b.execute(trial,args.out,180);print(json.dumps({k:r[k] for k in ['id','wall_s','correct','total','compliant','jev_api_calls']}),flush=True)
