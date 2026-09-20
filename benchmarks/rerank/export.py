#!/usr/bin/env python3
"""Export benchmark metrics/IDs and authored-fixture patches, never native logs."""
import argparse, hashlib, json, platform, re, subprocess, sys
from pathlib import Path

def load(path):return json.loads(path.read_text())
def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def sha(text):return hashlib.sha256(text.encode()).hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--experiment',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 source=a.experiment;exported={};patches=[]
 for kind in ['coding','retrieval']:
  plan=load(source/kind/'plan.json');save(a.out/f'{kind}-plan.json',plan);rows=[]
  for trial in plan['trials']:
   row=load(source/kind/trial['id']/'result.json')
   if row['id']!=trial['id']:raise ValueError('trial_mismatch')
   # Runner result schema contains only IDs, metrics, status, model and usage.
   if any(k in row for k in ['prompt','replacement','source_text','stderr','env']):raise ValueError('unexpected_raw_field')
   rows.append(row)
   if kind=='coding':
    events=[json.loads(line) for line in (source/kind/trial['id']/'main-native/events.jsonl').read_text().splitlines() if line.strip()]
    event=next(e for e in reversed(events) if e.get('type')=='result')
    answer=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',event['result'].strip()))
    if set(answer)!={'candidate_id','replacement'}:raise ValueError('unexpected_patch_schema')
    patches.append({'id':trial['id'],'task':trial['task'],'candidate_id':answer['candidate_id'],'replacement':answer['replacement'],'passed':row['passed']})
  exported[kind]=rows
 save(a.out/'runs.json',exported);save(a.out/'patches.json',patches)
 data=load(source/'public-data/input.json')
 save(a.out/'sample-manifest.json',{'input_sha256':hashlib.sha256((source/'public-data/input.json').read_bytes()).hexdigest(),'cases':[{'id':c['id'],'query_sha256':sha(c['query']),'gold_ids':c['gold_ids'],'candidates':[{'id':d['id'],'text_sha256':sha(d['text'])} for d in c['candidates']]} for c in data['cases']]})
 provenance=load(source/'public-data/provenance.json');provenance['artifacts'].pop('raw_data_location',None)
 save(a.out/'provenance.json',provenance)
 save(a.out/'environment.json',{'platform':platform.system(),'release':platform.release(),'machine':platform.machine(),'python':platform.python_version(),'node':subprocess.check_output(['node','--version'],text=True).strip(),'claude_cli':subprocess.check_output(['claude','--version'],text=True).strip(),'model_profile':load(source/'coding/plan.json')['model'],'native_jobs':'serial fresh sessions; tools disabled','raw_logs_published':False,'dataset_text_published':False})
 print(json.dumps({'coding_trials':len(exported['coding']),'retrieval_trials':len(exported['retrieval']),'authored_patches':len(patches)}))

if __name__=='__main__':main()
