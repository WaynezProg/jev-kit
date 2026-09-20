#!/usr/bin/env python3
"""Separate lower-tier quality assistance from higher-tier latency offloading."""
import argparse,hashlib,importlib.util,json,math,os,random,signal,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tier_host',ROOT.parent/'agent-ab/run.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
PROFILES={'haiku':{'host':'claude','model':'claude-haiku-4-5-20251001','effort':None},'fable':{'host':'claude','model':'claude-fable-5-1','effort':'low'}}
ARMS=['haiku_direct','haiku_assisted','fable_direct','fable_cascade']
LABELS={'supports','contradicts','insufficient'}

def sha(text):return hashlib.sha256(text.encode()).hexdigest()
def bound_rows(receipt,items):
 rows=receipt.get('results',[]);expected={r['id']:r for r in items}
 if len(rows)!=len(expected) or len({r.get('id') for r in rows})!=len(expected):return []
 for r in rows:
  v=expected.get(r.get('id'))
  if not v or r.get('source_sha256')!=sha(v['source_text']) or r.get('claim_sha256')!=sha(v['claim']):return []
 return rows

def projection(receipt,items,repeat):
 bound=bound_rows(receipt,items)
 accepted={r['id']:r['relation'] for r in bound if r.get('relation') in LABELS and r.get('requires_review') is False}
 audited=set(sorted(accepted,key=lambda id:sha(f'tier-audit:{repeat}:{id}'))[:math.ceil(len(accepted)*.1)])
 return {k:v for k,v in accepted.items() if k not in audited},audited

def prompt(items,advice=None):
 fixture={'mode':'evidence','input':{'items':items}}
 # The common task contract is identical; shuffle is performed once by the runner.
 text,_=host.prompt_for(fixture,'baseline',0)
 # prompt_for shuffles; both direct and assisted receive the same deterministic transformation.
 if advice is not None:
  text+='\nA separate probabilistic model provided the following advisory judgments. They can be wrong, even when confident. Independently check the original sources above; resolve uncertainty yourself. Do not use tools.\nADVICE:\n'+json.dumps(advice,ensure_ascii=False)
 return text

def execute(trial,fixture,out):
 folder=out/trial['id']
 if (folder/'result.json').exists():return json.loads((folder/'result.json').read_text())
 folder.mkdir(mode=0o700)
 items=list(fixture['input']['items']);random.Random(30920+trial['repeat']).shuffle(items)
 host.save(folder/'input.json',{'items':items})
 start=time.perf_counter();receipt={};jev_s=0;accepted={};audited=set();advice=None;provider_failure=False
 if trial['arm'] in ['haiku_assisted','fable_cascade']:
  before=time.perf_counter()
  try:child=subprocess.run(['node',str(ROOT/'judge.mjs'),str(folder/'input.json'),str(folder/'receipt.json')],capture_output=True,text=True,timeout=150)
  except subprocess.TimeoutExpired:child=None
  jev_s=time.perf_counter()-before
  if child and child.returncode==0:receipt=json.loads((folder/'receipt.json').read_text())
  bound=bound_rows(receipt,items);provider_failure=receipt.get('status')!='ok' or len(bound)!=len(items)
  if trial['arm']=='fable_cascade':accepted,audited=projection(receipt,items,trial['repeat'])
  else:advice=[{k:r.get(k) for k in ['id','relation','confidence','requires_review']} for r in bound]
 pending=[r for r in items if r['id'] not in accepted]
 profile=PROFILES[trial['arm'].split('_')[0]];parsed={'usage':None,'observed_models':[],'tool_calls':[],'host_reported_cost_usd':None};scored={};exit_code=0;timeout=False;llm_s=0
 if pending:
  text=prompt(pending,advice);(folder/'prompt.txt').write_text(text)
  cmd,env,stdin=host.invocation({**profile,'effort':profile['effort'] or 'low'},'baseline',folder,text,'evidence')
  if profile['effort'] is None:
   index=cmd.index('--effort');del cmd[index:index+2]
  before=time.perf_counter()
  with (folder/'events.jsonl').open('w') as stdout,(folder/'stderr.txt').open('w') as stderr:
   child=subprocess.Popen(cmd,cwd=folder,env=env,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,text=True,start_new_session=True)
   try:child.communicate(stdin,timeout=240)
   except subprocess.TimeoutExpired:
    timeout=True;os.killpg(child.pid,signal.SIGTERM)
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
  llm_s=time.perf_counter()-before;exit_code=child.returncode
  parsed=host.parse_log('claude',host.events(folder/'events.jsonl'),folder)
  subset={'gold':[r for r in fixture['gold'] if r['id'] not in accepted]}
  scored=host.score(subset,host.get_answer(parsed['answer_text']))
 final={**accepted,**{r['id']:r['choice'] for r in scored.get('predictions',[])}}
 finalscore=host.score(fixture,{'decisions':[{'id':k,'choice':v} for k,v in final.items()]})
 gold={r['id']:r['choice'] for r in fixture['gold']};calls=receipt.get('calls',[]);raw=bound_rows(receipt,items)
 result={**trial,'profile':profile,'wall_s':time.perf_counter()-start,'jev_s':jev_s,'llm_s':llm_s,**finalscore,
 'complete':exit_code==0 and not timeout and finalscore['schema_valid'] and scored.get('schema_valid',True) and not parsed['tool_calls'],
 'exit_code':exit_code,'timeout':timeout,'native_tool_attempts':len(parsed['tool_calls']),'observed_models':parsed['observed_models'],'usage':parsed['usage'],'host_reported_cost_usd':parsed['host_reported_cost_usd'],
 'llm_items':len(pending),'automated_items':len(accepted),'automated_errors':sum(v!=gold[k] for k,v in accepted.items()),'audited_ids':sorted(audited),
 'jev_api_calls':len(calls),'jev_models':sorted({c['model'] for c in calls if c.get('model')}),'provider_failure':provider_failure,
 'jev_input_tokens':sum(c.get('usage',{}).get('inputTokens',0) for c in calls),'jev_output_tokens':sum(c.get('usage',{}).get('outputTokens',0) for c in calls),
 'jev_raw_correct':sum(r.get('relation')==gold.get(r['id']) for r in raw),'jev_bound_rows':len(raw),'jev_review_items':sum(r.get('requires_review',True) for r in raw),
 'jev_unflagged_errors':sum(r.get('relation')!=gold.get(r['id']) for r in raw if r.get('requires_review') is False)}
 host.save(folder/'result.json',result);return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--plan-only',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True,mode=0o700)
 fixture=json.loads((ROOT/'evidence.json').read_text());trials=[]
 for rep in range(1,4):
  order=ARMS[(rep-1)%4:]+ARMS[:(rep-1)%4]
  trials.extend({'id':f'r{rep}-{arm}','arm':arm,'repeat':rep} for arm in order)
 plan={'fixture_sha256':hashlib.sha256((ROOT/'evidence.json').read_bytes()).hexdigest(),'profiles':PROFILES,'trials':trials,
 'design':'48 newly authored cases, 16 per label, one distinct source each. Three repeats; serial fresh Claude Code sessions; rotated arm order; prepared inputs through code; no answer-key exposure; no scored outcome tuning.',
 'lower_tier_gate':{'accuracy_gain_percentage_points':5,'all_runs_complete':True,'comparison':'Haiku assisted versus Haiku direct; compare Fable direct separately as the upgrade alternative.'},
 'higher_tier_gate':{'aggregate_accuracy_no_regression':True,'each_repeat_accuracy_no_regression':True,'median_wall_reduction':.30,'max_automated_error_rate':.01,'all_runs_complete':True},
 'cascade_policy':'Unchanged production requires_review threshold plus deterministic 10 percent audit (rounded up). Source AND claim hashes bind inputs. Unresolved/provider-failed items go to the main model.',
 'limitations':'Authored screening, not blind external adjudication or production task outcomes. Repeats are not independent cases. Haiku uses default effort; Fable uses low effort. Host cost estimates are not subscription bills.'}
 if (a.out/'plan.json').exists():assert json.loads((a.out/'plan.json').read_text())==plan
 else:host.save(a.out/'plan.json',plan)
 if a.plan_only:print('Frozen',len(trials),'trials',plan['fixture_sha256']);return
 for trial in trials:
  result=execute(trial,fixture,a.out);print(json.dumps({k:result[k] for k in ['id','correct','total','wall_s','llm_items','automated_errors','jev_raw_correct','complete']}),flush=True)
if __name__=='__main__':main()
