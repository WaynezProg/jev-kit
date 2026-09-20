"""Additional host cohort, frozen separately from the primary 48 runs."""
import argparse,json
from pathlib import Path
import run as b
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--plan-only',action='store_true');p.add_argument('--probe',action='store_true');p.add_argument('--probe-host',choices=['opencode','grok']);args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True,mode=0o700)
profiles=[{'id':'opencode-luna-low','host':'opencode','model':'openai/gpt-5.6-luna','effort':'low'},{'id':'grok-46-low','host':'grok','model':'grok-4.6','effort':'low'}]
if args.probe:
 for profile in profiles:
  if args.probe_host and args.probe_host!=profile['host']:continue
  fixture={'mode':'evidence','input':{'items':[{'id':'probe','claim':'Deployment is complete.','source_text':'Deployment has not started.','source_ref':'synthetic'}]}}
  folder=args.out/profile['id'];folder.mkdir(mode=0o700)
  prompt,_=b.prompt_for(fixture,'jev',1);(folder/'prompt.txt').write_text(prompt)
  cmd,env,stdin=b.invocation(profile,'jev',folder,prompt,'evidence')
  import subprocess,time,os,signal
  start=time.perf_counter()
  with (folder/'events.jsonl').open('w') as out,(folder/'stderr.txt').open('w') as err:
   child=subprocess.Popen(cmd,cwd=folder,env=env,stdin=subprocess.PIPE,stdout=out,stderr=err,text=True,start_new_session=True)
   try:child.communicate(stdin,timeout=100)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=5)
  parsed=b.parse_log(profile['host'],b.events(folder/'events.jsonl'),folder)
  b.save(folder/'probe.json',{'exit_code':child.returncode,'seconds':time.perf_counter()-start,**parsed})
  print(profile['id'],child.returncode,parsed['answer_text'],parsed['usage'],flush=True)
else:
 trials=[]
 for repeat in [1,2]:
  for index,profile in enumerate(profiles):
   for wi,workload in enumerate(b.WORKLOADS):
    for arm in (['baseline','jev'] if (index+wi+repeat)%2 else ['jev','baseline']):trials.append({'id':f'{profile["id"]}-{workload}-r{repeat}-{arm}','profile':profile,'workload':workload,'repeat':repeat,'arm':arm})
 plan={'design':'Additional cohort: two hosts, two repeats, both tasks, paired and counterbalanced. Separate phase, not pooled with primary timing.','timeout_s':180,'trials':trials}
 if (args.out/'plan.json').exists():assert json.loads((args.out/'plan.json').read_text())==plan
 else:b.save(args.out/'plan.json',plan)
 if args.plan_only:print('Frozen',len(trials),'additional host trials')
 else:
  for trial in trials:
   r=b.execute(trial,args.out,180);print(json.dumps({k:r[k] for k in ['id','wall_s','correct','total','completed','compliant','jev_api_calls']}),flush=True)
