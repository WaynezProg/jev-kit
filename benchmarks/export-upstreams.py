"""Publish allowlisted numeric receipts; private model transcripts stay outside repo."""
import json, sys, statistics, subprocess, hashlib
from pathlib import Path
BASE=Path(sys.argv[1]);ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def selected(obj,keys):return {k:obj[k] for k in keys if k in obj}
def median(xs):return statistics.median(xs) if xs else None
for source,target in [('compaction/replay-v1','upstream-compaction'),('compaction/continuation-v1','upstream-compaction'),('foreman/replay-v1','upstream-foreman'),('foreman/native-v1','upstream-foreman'),('foreman/native-v2','upstream-foreman'),('browser/ego-v3','ego-upstream'),('browser/ego-v4','ego-upstream')]:
 plan=load(BASE/source/'plan.json')
 if source=='compaction/replay-v1':
  plan['cases']=[{**selected(c,['id','goal','gold']),'messages_sha256':hashlib.sha256(json.dumps(c['messages'],separators=(',',':'),ensure_ascii=False).encode()).hexdigest()} for c in plan['cases']]
 save(ROOT/f'benchmarks/{target}/results/{Path(source).name}-plan.json',plan)

cr=load(BASE/'compaction/replay-v1/results.json'); cc=load(BASE/'compaction/continuation-v1/results.json')
crows=[]
for x in cr:
 y=selected(x,['id','repeat','seconds','before_bytes','after_bytes','recency_bytes','retained','recency_retained','pairs_valid','recency_pairs_valid','stats','calls','decisions','error'])
 if 'after_bytes' in x:y['recency_budget_met']=x['recency_bytes']<=x['after_bytes']
 crows.append(y)
cs={'upstream_sha':'e3f262a7f4d42bd8dd32ced30d26176f7cb545b0','offline_tests':29,'runs':len(cr),'all_facts_retained':sum(all(x.get('retained',[])) for x in cr if 'retained' in x),'median_reduction_serialized_bytes':median([1-x['after_bytes']/x['before_bytes'] for x in cr]),'median_compaction_seconds':median([x['seconds'] for x in cr]),'continuation':{}}
for arm in ['full','jev','recency']:
 rows=[x for x in cc if x['arm']==arm]
 times=[x['seconds']+(next(r['seconds'] for r in cr if r['id']==x['id'] and r['repeat']==1) if arm=='jev' else 0) for x in rows]
 cs['continuation'][arm]={'n':len(rows),'correct':sum(x['correct'] for x in rows),'median_continuation_seconds':median([x['seconds'] for x in rows]),'median_with_compaction_seconds':median(times),'claude_reported_cost_usd_excluding_jev':sum(x['host_cost_usd'] or 0 for x in rows)}
save(ROOT/'benchmarks/upstream-compaction/results/replay.json',crows);save(ROOT/'benchmarks/upstream-compaction/results/continuation.json',cc);save(ROOT/'benchmarks/upstream-compaction/results/summary.json',cs)

fr=load(BASE/'foreman/replay-v1/results.json');save(ROOT/'benchmarks/upstream-foreman/results/replay.json',fr)
fs={'upstream_sha':'3de1556a59b7a7e14daa1f89b2fc49080bbb8cce','offline_tests':80,'synthetic_allowed_actions':sum(r.get('correct',False) for r in fr),'synthetic_attempts':len(fr),'synthetic_status_only_baseline':sum(r.get('baseline_correct',False) for r in fr),'median_assessment_seconds':median([r['seconds'] for r in fr]),'native':{}}
session_files=subprocess.check_output(['rg','--files',str(Path.home()/'.codex/sessions')],text=True).splitlines()
for version in ['native-v1','native-v2']:
 raw=load(BASE/f'foreman/{version}/results.json');rows=[]
 for r in raw:
  row=selected(r,['id','arm','seconds','passed','check_exit','status','jev_calls']);row['workers']=[];row['interventions']=[selected(a,['action','reason']) for a in r['interventions']]
  for worker in r['workers']:
   meta=selected(worker,['worker_type','status','exit_code','termination_reason']);models=[];usage=None
   for path in session_files:
    if worker.get('codex_thread_id') and worker['codex_thread_id'] in path:
     for line in Path(path).read_text().splitlines():
      item=json.loads(line);payload=item.get('payload',{})
      if item.get('type')=='turn_context':models.append(selected(payload,['model','effort']))
      if item.get('type')=='event_msg' and payload.get('type')=='token_count':usage=(payload.get('info') or {}).get('total_token_usage') or usage
   meta['observed_models']=list({json.dumps(m,sort_keys=True):m for m in models}.values());meta['total_token_usage']=usage;row['workers'].append(meta)
  rows.append(row)
 save(ROOT/f'benchmarks/upstream-foreman/results/{version}.json',rows)
 fs['native'][version]={arm:{'attempts':len(part),'external_checks_passed':sum(r['passed'] for r in part),'runtime_finished':sum(r['status'] in ['FINISHED','completed'] for r in part),'median_seconds':median([r['seconds'] for r in part]),'jev_assessments':sum(r['jev_calls'] for r in part)} for arm in ['direct','foreman'] if (part:=[r for r in rows if r['arm']==arm])}
save(ROOT/'benchmarks/upstream-foreman/results/summary.json',fs)

bs={'upstream_sha':'1231850a0bf1a0c0341fe408ef1668dbbfdfac46','offline_tests':31,'versions':{}}
for version in ['ego-v1','ego-v2','ego-v3','ego-v4']:
 directory=BASE/f'browser/{version}'
 raw=[load(p) for p in sorted(directory.glob('*/result.json'))]
 rows=[]
 for r in raw:
  row=selected(r,['id','repeat','arm','title','status','verified','total_seconds','claude_turns','claude_usage','claude_host_cost_usd'])
  # Errors can contain local paths/ephemeral selectors; retain category, not text.
  error=r.get('error');row['error_category']=None if not error else 'stale' if 'stale' in error else 'timeout' if 'timed out' in error or 'timeout' in error else 'origin' if 'origin' in error else 'navigation' if 'page.goto' in error else 'page_unavailable' if 'page_unavailable' in error else 'runtime_error'
  row['steps']=[selected(s,['step','operation','choice','model','confidence','usage','decision_s','text_model','text_s','text_usage','browser_s','discarded','executed']) for s in r.get('steps',[])];rows.append(row)
 save(ROOT/f'benchmarks/ego-upstream/results/{version}.json',rows)
 status='invalid comparison: missing Claude executable' if version=='ego-v1' else 'invalid comparison: prior embedded script still active' if version=='ego-v2' else 'frozen complete comparison' if version=='ego-v3' else 'follow-up after navigation synchronization changes'
 entry={'interpretation':status,'complete_receipt':(directory/'results.json').exists(),'cohorts':{}}
 for cohort in ['local','public']:
  entry['cohorts'][cohort]={}
  for arm in ['jev','claude']:
   part=[r for r in rows if r['arm']==arm and r['id'].startswith('wikipedia')==(cohort=='public')]
   entry['cohorts'][cohort][arm]={'n':len(part),'verified':sum(r.get('verified',False) for r in part),'median_attempt_seconds':median([r['total_seconds'] for r in part]),'claude_turns':sum(r['claude_turns'] for r in part),'jev_decisions':sum(len(r['steps']) for r in part if arm=='jev')}
 if (directory/'guards.json').exists():entry['guards']=load(directory/'guards.json')
 bs['versions'][version]=entry
save(ROOT/'benchmarks/ego-upstream/results/summary.json',bs)
print(json.dumps({'compaction':cs,'foreman':fs,'browser':bs},indent=2))
