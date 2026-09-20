#!/usr/bin/env python3
"""Publish only allowlisted benchmark numbers/labels, never raw CLI logs or machine paths."""
import argparse,json,statistics
from pathlib import Path
import run as b

def median(rows,key):
 values=[r[key] for r in rows if r.get(key) is not None]
 return statistics.median(values) if values else None

def input_equivalent(a,c,mode):
 a=json.loads(json.dumps(a));c=json.loads(json.dumps(c))
 if mode=='evidence':
  for d in [a,c]:
   for r in d.get('items',[]):
    if r.get('quote') is None:r.pop('quote',None)
 # Reordering changes batch composition but does not alter source text or row bindings.
 for d in [a,c]:d['items']=sorted(d.get('items',[]),key=lambda r:r.get('id',''))
 return a==c

def normalize(folder,phase):
 old=json.loads((folder/'result.json').read_text());logs=b.events(folder/'events.jsonl');p=b.parse_log(old['profile']['host'],logs,folder)
 usage=p['usage'];host=old['profile']['host']
 seen=(any(e.get('type')=='turn.completed' and isinstance(e.get('usage'),dict) for e in logs) if host=='codex' else any(e.get('type')=='message_end' and isinstance(e.get('message',{}).get('usage'),dict) for e in logs) if host=='pi' else any(e.get('type')=='step_finish' and isinstance(e.get('part',{}).get('tokens'),dict) for e in logs) if host=='opencode' else usage is not None)
 if not seen:usage=None
 fixture=json.loads((b.ROOT/(old['workload']+'.json')).read_text());answer=b.get_answer(p['answer_text']);score=b.score(fixture,answer)
 labels={r['choice'] for r in fixture['gold']}
 if isinstance(answer,dict):score['schema_valid']=score['schema_valid'] and all(isinstance(r.get('choice'),str) and r['choice'] in labels for r in answer.get('decisions',[]))
 traces=b.events(folder/'jev.jsonl');expected=json.loads((folder/'input.json').read_text())
 receipts=[r['result'] for r in traces] or p['native_receipts']
 errors=[];attempts=[];wire_inputs=[]
 for e in logs:
  if host=='codex' and e.get('type')=='item.completed' and e.get('item',{}).get('type')=='mcp_tool_call':
   i=e['item'];attempts.append(i.get('tool'));wire_inputs.append(i.get('arguments'))
   for part in (i.get('result') or {}).get('content',[]):
    t=part.get('text','')
    if t.startswith('MCP error'):errors.append('duplicate_ids' if 'IDs must be unique' in t else 'mcp_validation_or_execution_error')
  elif host=='claude' and e.get('type')=='user':
   for part in e.get('message',{}).get('content',[]):
    if part.get('type')=='tool_result' and part.get('is_error'):errors.append('mcp_validation_or_execution_error')
  elif host=='pi' and e.get('type')=='tool_execution_end' and e.get('isError'):errors.append('tool_execution_error')
  elif host=='opencode' and e.get('type')=='tool_use' and e.get('part',{}).get('state',{}).get('status')=='error':errors.append('mcp_validation_or_execution_error')
  elif host=='grok':
   for part in e.get('message',e).get('content',[]):
    if part.get('type')=='tool_use' and 'jev_' in str(part.get('name')):wire_inputs.append(part.get('input'))
    elif part.get('type')=='tool_use' and part.get('name')=='use_tool' and 'jev_' in str(part.get('input',{}).get('tool_name')):wire_inputs.append(part['input'].get('tool_input'))
    if part.get('type')=='tool_result' and part.get('is_error'):errors.append('mcp_validation_or_execution_error')
 if traces:source_preserved=all(input_equivalent(t['input'],expected,fixture['mode']) for t in traces)
 elif receipts and wire_inputs:source_preserved=all(isinstance(t,dict) and input_equivalent(t,expected,fixture['mode']) for t in wire_inputs)
 else:source_preserved=None
 strict_equal=all(t['input']==expected for t in traces) if traces else all(t==expected for t in wire_inputs) if wire_inputs else None
 calls=[c for r in receipts for c in r.get('calls',[])];items=[i for r in receipts for i in r.get('results',[])];gold={r['id']:r['choice'] for r in fixture['gold']}
 raw_predictions={r.get('id'):r.get('relation',r.get('classification')) for r in items}
 final={r['id']:r['choice'] for r in score['predictions']}
 row={
  'run_key':phase+'/'+old['id'],
  'id':old['id'],'phase':phase,'profile':old['profile']['id'],'host':host,'requested_model':old['profile']['model'],'effort':old['profile']['effort'],'observed_models':p['observed_models'],'workload':old['workload'],'repeat':old['repeat'],'arm':old['arm'],
  'wall_s':round(old['wall_s'],4),'exit_code':old['exit_code'],'timeout':old['timeout'],'completed':not old['timeout'] and old['exit_code']==0 and score['schema_valid'],'correct':score['correct'],'total':score['total'],'schema_valid':score['schema_valid'],
  'main_input_tokens':usage['input'] if usage else None,'main_output_tokens':usage['output'] if usage else None,'main_cache_read_tokens':usage['cache_read'] if usage else None,'main_cache_write_tokens':usage['cache_write'] if usage else None,'main_reasoning_tokens':usage['reasoning'] if usage else None,'main_usage_complete':seen and not old['timeout'] and old['exit_code']==0,
  'native_tool_attempts':len(p['tool_calls']),'tool_errors':errors,'jev_successful_tool_calls':len(receipts),'source_preserved':source_preserved,'strict_input_equal':strict_equal,'jev_api_calls':len(calls),'jev_models':sorted({c['model'] for c in calls if c.get('model')}),'jev_input_tokens':sum(c.get('usage',{}).get('inputTokens',0) for c in calls),'jev_output_tokens':sum(c.get('usage',{}).get('outputTokens',0) for c in calls),'jev_s':round(sum(r.get('elapsed_ms',0) for r in receipts)/1000,4),'jev_review_items':sum(bool(i.get('requires_review')) for i in items),'jev_provider_errors':sum(bool(c.get('error')) for c in calls),
  'jev_raw_correct':sum(raw_predictions.get(i)==v for i,v in gold.items()) if receipts else None,
  'agent_changed_jev_labels':sum(i in raw_predictions and raw_predictions[i]!=final[i] for i in gold),
  'agent_fixed_jev_errors':sum(i in raw_predictions and raw_predictions[i]!=gold[i] and final[i]==gold[i] for i in gold),
  'agent_introduced_errors':sum(i in raw_predictions and raw_predictions[i]==gold[i] and final[i]!=gold[i] for i in gold),
  'jev_predictions':[{'id':i['id'],'choice':raw_predictions[i['id']] if isinstance(raw_predictions[i['id']],str) and raw_predictions[i['id']] in labels else None,'expected':gold[i['id']],'requires_review':bool(i.get('requires_review'))} for i in items if i.get('id') in gold],
  'predictions':[{'id':r['id'],'choice':r['choice'] if isinstance(r['choice'],str) and r['choice'] in labels else None,'expected':r['expected']} for r in score['predictions']],
 }
 row['intervention_valid']=(row['jev_successful_tool_calls']==1 and source_preserved is True and row['jev_api_calls']>0 and row['jev_provider_errors']==0) if row['arm']!='baseline' else row['native_tool_attempts']==0
 return row

def groups(rows):
 table=[]
 for phase,profile,workload in sorted({(r['phase'],r['profile'],r['workload']) for r in rows}):
  selected=[r for r in rows if (r['phase'],r['profile'],r['workload'])==(phase,profile,workload)]
  baseline=[r for r in selected if r['arm']=='baseline'];other=[r for r in selected if r['arm']!='baseline']
  if not baseline or not other:continue
  ratios=[];deltas=[]
  for a in baseline:
   match=next((r for r in other if r['repeat']==a['repeat']),None)
   if match:ratios.append(match['wall_s']/a['wall_s']);deltas.append(match['wall_s']-a['wall_s'])
  def arm(rs):
   return {'runs':len(rs),'completed':sum(r['completed'] for r in rs),'valid_interventions':sum(r['intervention_valid'] for r in rs),'correct':sum(r['correct'] for r in rs),'total':sum(r['total'] for r in rs),'median_wall_s':median(rs,'wall_s'),'min_wall_s':min(r['wall_s'] for r in rs),'max_wall_s':max(r['wall_s'] for r in rs),'median_main_input_tokens':median(rs,'main_input_tokens'),'median_main_output_tokens':median(rs,'main_output_tokens'),'median_cache_read_tokens':median(rs,'main_cache_read_tokens'),'median_jev_input_tokens':median(rs,'jev_input_tokens'),'median_jev_output_tokens':median(rs,'jev_output_tokens'),'median_jev_s':median(rs,'jev_s'),'jev_review_items':sum(r['jev_review_items'] for r in rs),'agent_fixed_jev_errors':sum(r['agent_fixed_jev_errors'] for r in rs),'agent_introduced_errors':sum(r['agent_introduced_errors'] for r in rs)}
  table.append({'phase':phase,'profile':profile,'workload':workload,'comparison_arm':other[0]['arm'],'baseline':arm(baseline),'assisted':arm(other),'paired_median_wall_ratio':statistics.median(ratios),'paired_median_extra_s':statistics.median(deltas)})
 return table

def markdown(rows,summary,direct):
 text=['# Agent benchmark results — 2026-09-20','', 'Real CLI/model calls over controlled source-evidence and issue-routing tasks. See [methodology](../README.md). These are repeated observations of 43 records, not independent production tasks.','',
 '| Phase | Profile | Workload | Baseline correct | Jev-arm correct | Baseline median s | Jev-arm median s | Paired median time ratio | Valid Jev calls |',
 '|---|---|---|---:|---:|---:|---:|---:|---:|']
 for group in summary:
  a,c=group['baseline'],group['assisted']
  text.append(f"| {group['phase']} | {group['profile']} | {group['workload']} | {a['correct']}/{a['total']} | {c['correct']}/{c['total']} | {a['median_wall_s']:.2f} | {c['median_wall_s']:.2f} | {group['paired_median_wall_ratio']:.2f}× | {c['valid_interventions']}/{c['runs']} |")
 text+=['','A valid Jev intervention requires one completed call with preserved input records. Rejected or altered-input calls remain in the assigned-arm accuracy and timing totals. A correct final answer does not establish that Jev helped. Failed/timeout attempts are retained. Paired ratios are medians of matched-repeat ratios, not ratios of the two arm medians; these can point in different directions in a small noisy sample.','', '## Main-model tokens and Jev service work','', '| Profile | Workload | Phase | Median main input: direct → Jev | Median main output: direct → Jev | Median cached input: direct → Jev | Median Jev input/output | Median Jev service s |', '|---|---|---|---:|---:|---:|---:|---:|']
 def show(v):return 'not reported' if v is None else f'{v:,.0f}'
 for g in summary:
  a,c=g['baseline'],g['assisted'];text.append(f"| {g['profile']} | {g['workload']} | {g['phase']} | {show(a['median_main_input_tokens'])} → {show(c['median_main_input_tokens'])} | {show(a['median_main_output_tokens'])} → {show(c['median_main_output_tokens'])} | {show(a['median_cache_read_tokens'])} → {show(c['median_cache_read_tokens'])} | {show(c['median_jev_input_tokens'])} / {show(c['median_jev_output_tokens'])} | {c['median_jev_s']:.2f} |")
 text+=['','Input totals include cached input once. Output includes reasoning once where reported; OpenCode exposes it separately, so its output and reasoning fields are recombined. An unavailable reasoning breakdown is null. Token totals are not dollar charges; Muse main-model usage is absent from its CLI events. Host contexts differ, so use within-profile comparisons.','', '## Standalone Jev engine (no agent review)','', '| Input order | Workload | Median s | Raw correct | Accepted correct | Held for review |', '|---|---|---:|---:|---:|---:|']
 for order in ['source-grouped','agent-shuffled']:
  for name in b.WORKLOADS:
   rs=[r for r in direct if r['workload']==name and r['order']==order]
   if rs:text.append(f"| {order} | {name} | {median(rs,'wall_s'):.2f} | {sum(r['correct'] for r in rs)}/{sum(r['total'] for r in rs)} | {sum(r['accepted_correct'] for r in rs)}/{sum(r['accepted'] for r in rs)} | {sum(r['review'] for r in rs)} |")
 text+=['','Standalone engine timings exclude host reasoning/review and are not directly equivalent to finished agent answers. Accepted means not flagged for review, not independently certified correct.','', '## Limitations','', '- Small sample: three repeats in primary/file cohorts; two in additional-host cohort. No statistical significance or universal speed/cost improvement claim.','- Gold labels are authored from source semantics/routing rules; no independent external annotation.','- Real authenticated services and native CLIs were used, but tasks are controlled judgments, not full repository repair or feature delivery.','- Provider caching, network latency, model scheduling and host context contribute to wall-time differences. Phase comparisons are exploratory; fresh baselines exist within each phase.','- Fixed-file tools exist only in this benchmark adapter. The standard plugin still expects inline structured MCP inputs; its CLI already accepts input files.','- Missing model usage is not zero. No subscription invoice or Jev monetary charge was measured.','- Raw private CLI logs are excluded; public predictions, labels, usage, timings and per-call success counters are in `runs.json`.','']
 text+=['## Incomplete or noncompliant attempts','','All rows below remain in the assigned-arm totals. A changed source can be semantically harmless, but it fails exact source preservation.','', '| Trial | Final schema complete | Source preserved | Jev API calls | Tool error |','|---|---|---|---:|---|']
 for r in rows:
  if not r['completed'] or not r['intervention_valid']:
   text.append(f"| {r['run_key']} | {r['completed']} | {r['source_preserved']} | {r['jev_api_calls']} | {', '.join(r['tool_errors']) or '—'} |")
 text+=['','## Agent review of Jev labels','','Only interventions with preserved input and successful Jev API calls appear here. These are descriptive comparisons, not independent model evaluations.','', '| Phase / profile / task | Raw Jev correct | Final agent correct | Agent fixed Jev errors | Agent introduced errors | Items flagged for review |','|---|---:|---:|---:|---:|---:|']
 for g in summary:
  rs=[r for r in rows if r['phase']==g['phase'] and r['profile']==g['profile'] and r['workload']==g['workload'] and r['arm']!='baseline' and r['intervention_valid']]
  if not rs:continue
  total=sum(r['total'] for r in rs)
  text.append(f"| {g['phase']} / {g['profile']} / {g['workload']} | {sum(r['jev_raw_correct'] for r in rs)}/{total} | {sum(r['correct'] for r in rs)}/{total} | {sum(r['agent_fixed_jev_errors'] for r in rs)} | {sum(r['agent_introduced_errors'] for r in rs)} | {sum(r['jev_review_items'] for r in rs)} |")
 text+=['']
 return '\n'.join(text)

def main():
 p=argparse.ArgumentParser();p.add_argument('--private',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--partial',action='store_true');args=p.parse_args();rows=[];plans={}
 for folder_name,phase in [('main','primary'),('file-study','file-adapter'),('additional','additional-hosts')]:
  folder=args.private/folder_name
  if not (folder/'plan.json').exists():continue
  plan=json.loads((folder/'plan.json').read_text());plans[phase]=plan
  for trial in plan['trials']:
   folder2=folder/trial['id']
   if not (folder2/'result.json').exists():
    if args.partial:continue
    raise SystemExit('Missing scheduled trial: '+trial['id'])
   rows.append(normalize(folder2,phase))
 direct=[]
 for folder,order in [('direct','source-grouped'),('direct-shuffled','agent-shuffled')]:
  for path in sorted((args.private/folder).glob('*.json')):
   r=json.loads(path.read_text());r.pop('receipt',None);r['order']=order;direct.append(r)
 if (args.private/'direct-order-plan.json').exists():plans['standalone-order']=json.loads((args.private/'direct-order-plan.json').read_text())
 if not args.partial and len(direct)!=12:raise SystemExit('Expected twelve standalone comparisons across both input orders')
 summary=groups(rows);args.out.mkdir(parents=True,exist_ok=True)
 environment=json.loads((args.private/'environment.json').read_text()) if (args.private/'environment.json').exists() else {}
 environment={k:environment[k] for k in ['date','os','architecture','python','node','cli_versions','source_revision','reasoning_request','raw_logs_public'] if k in environment}
 for name,data in [('runs.json',rows),('summary.json',summary),('plans.json',plans),('direct.json',direct)]:
  (args.out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 (args.out/'environment.json').write_text(json.dumps(environment,ensure_ascii=False,indent=2)+'\n')
 availability=json.loads((args.private/'availability.json').read_text()) if (args.private/'availability.json').exists() else []
 availability=[{k:r[k] for k in ['profile','requested_model','phase','status','http_status','reason','replacement'] if k in r} for r in availability]
 (args.out/'availability.json').write_text(json.dumps(availability,ensure_ascii=False,indent=2)+'\n')
 (args.out/'RESULTS.md').write_text(markdown(rows,summary,direct))
 print(json.dumps({'agent_runs':len(rows),'groups':len(summary),'direct_runs':len(direct),'output':str(args.out)}))
if __name__=='__main__':main()
