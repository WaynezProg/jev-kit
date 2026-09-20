#!/usr/bin/env python3
"""Publish measured outcomes, never native transcripts, source paths or credentials."""
import argparse,json,statistics
from pathlib import Path
ARMS=['keywords','llm_plan','llm_step','jev_step']
med=statistics.median

def summarize(rows):
 groups={}
 for arm in ARMS:
  runs=[r for r in rows if r['arm']==arm];success=[r for r in runs if r['success']]
  groups[arm]={'attempts':len(runs),'successes':len(success),'blocked':sum(r['outcome']=='blocked' for r in runs),'uncertain':sum(r['outcome']=='uncertain' for r in runs),'invalid':sum(r['error'] in ['invalid_action','invalid_decision_schema','invalid_plan'] for r in runs),'other_errors':sum(r['outcome']=='error' and r['error'] not in ['invalid_action','invalid_decision_schema','invalid_plan'] for r in runs),'wrong_clicks':sum(r['wrong_clicks'] for r in runs),'median_attempt_wall_s':med(r['wall_s'] for r in runs),'median_success_wall_s':med(r['wall_s'] for r in success) if success else None,'median_decision_s':med(r['decision_s'] for r in runs),'median_planner_s':med(r['planner_s'] for r in runs),'median_browser_s':med(r['browser_s'] for r in runs),'main_calls':sum(r['main_calls'] for r in runs),'jev_calls':sum(r['jev_calls'] for r in runs),'median_main_api_s':med(r['native_duration_api_ms']/1000 for r in runs) if all(r['native_duration_api_ms'] is not None for r in runs) else None,'main_input_tokens':sum(r['main_input_tokens'] for r in runs),'main_output_tokens':sum(r['main_output_tokens'] for r in runs),'jev_input_tokens':sum(r['jev_input_tokens'] for r in runs),'jev_output_tokens':sum(r['jev_output_tokens'] for r in runs)}
 jev=groups['jev_step'];comparisons={}
 for arm in ARMS[:-1]:
  base=groups[arm];by={(r['task_id'],r['repeat']):r for r in rows if r['arm']==arm}
  pairs=[(by[r['task_id'],r['repeat']],r) for r in rows if r['arm']=='jev_step' and r['success'] and by[r['task_id'],r['repeat']]['success']]
  comparisons[arm]={'paired_success_count':len(pairs),'median_paired_reduction':med(1-j['wall_s']/b['wall_s'] for b,j in pairs) if pairs else None,'pooled_median_attempt_reduction':1-jev['median_attempt_wall_s']/base['median_attempt_wall_s']}
 checks={'jev_all_24_complete':jev['successes']==24 and jev['attempts']==24,'matches_every_comparator_success_count':all(jev['successes']>=groups[a]['successes'] for a in ARMS[:-1]),'wall_reduction_vs_llm_step_30pct':comparisons['llm_step']['pooled_median_attempt_reduction']>=.30,'wall_reduction_vs_llm_plan_20pct':comparisons['llm_plan']['pooled_median_attempt_reduction']>=.20}
 return {'groups':groups,'comparisons':comparisons,'frozen_gate':{'checks':checks,'pass':all(checks.values())}}

def publish_row(path):
 r=json.loads(path.read_text());r.pop('native_usage',None)
 # Claude's result-event usage is per-turn; costs/API duration are cumulative.
 events=[]
 if (path.parent/'events.jsonl').exists():
  for line in (path.parent/'events.jsonl').read_text().splitlines():
   try:e=json.loads(line)
   except ValueError:continue
   if e.get('type')=='result':events.append(e)
 r['main_input_tokens']=sum(sum(e.get('usage',{}).get(k,0) for k in ['input_tokens','cache_read_input_tokens','cache_creation_input_tokens']) for e in events)
 r['main_output_tokens']=sum(e.get('usage',{}).get('output_tokens',0) for e in events)
 r['main_cache_read_tokens']=sum(e.get('usage',{}).get('cache_read_input_tokens',0) for e in events)
 r['main_thinking_tokens']=sum(e.get('usage',{}).get('output_tokens_details',{}).get('thinking_tokens',0) for e in events)
 if r['error'] and (r['error'].startswith('/') or '/Users/' in r['error']):r['error']='runtime_error_private_details_omitted'
 return r

def main():
 p=argparse.ArgumentParser();p.add_argument('--raw',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(exist_ok=True,parents=True)
 rows=[publish_row(p) for p in sorted(a.raw.glob('*/result.json'))];assert len(rows)==96
 summary=summarize(rows)
 for name,data in [('runs.json',rows),('summary.json',summary),('plan.json',json.loads((a.raw/'plan.json').read_text()))]:(a.out/name).write_text(json.dumps(data,indent=2)+'\n')
 fmt=lambda n:'—' if n is None else f'{n:.2f}'
 lines=['# Matched browser-loop results','','**Eight authored local semantic wizards, three repeats, actual Ego Lite interactions and real API/model calls.** These are not 96 independent production tasks or an open-web reliability benchmark. All 96 attempts are retained.','','| Path | Verified completed | Blocked / uncertain | Wrong clicks | Median all-attempt seconds | Median successful seconds | Main / Jev calls |','|---|---:|---:|---:|---:|---:|---:|']
 for arm,r in summary['groups'].items():lines.append(f"| {arm} | {r['successes']}/{r['attempts']} | {r['blocked']} / {r['uncertain']} | {r['wrong_clicks']} | {r['median_attempt_wall_s']:.2f} | {fmt(r['median_success_wall_s'])} | {r['main_calls']} / {r['jev_calls']} |")
 lines+=['','A blocked run that ends early is unresolved work, not a fast successful task. The rules baseline abstains on zero/tied matches; its failure count is not a count of harmful actions. The plan baseline generates semantic terms once and uses a fixed matcher; it is not an unrestricted coding agent.','','| Model path | Median decision seconds | Median planning seconds | Median browser seconds | Median native API seconds |','|---|---:|---:|---:|---:|']
 for arm in ['llm_plan','llm_step','jev_step']:
  r=summary['groups'][arm];lines.append(f"| {arm} | {r['median_decision_s']:.2f} | {r['median_planner_s']:.2f} | {r['median_browser_s']:.2f} | {fmt(r['median_main_api_s'])} |")
 lines+=['','Native process startup is included in wall/decision or planner time; Claude remains running between steps. Native API duration is reported separately. Component medians need not sum to the median total. Browser work also measured differently across arms (same executor, different decision cadence), so the full wall-time gain must not be attributed solely to the Jev API. Browser time includes clicks and subsequent observations; one-time fixture setup, navigation and the first observation are excluded equally. Final independent verification is included.','','| Jev comparison | Jointly successful task/repeat pairs | Median paired time reduction |','|---|---:|---:|']
 for arm,r in summary['comparisons'].items():lines.append(f"| vs {arm} | {r['paired_success_count']} | {fmt(100*r['median_paired_reduction']) if r['median_paired_reduction'] is not None else '—'}% |")
 lines+=['',f"Frozen practical screen: **{'PASS' if summary['frozen_gate']['pass'] else 'FAIL'}**. All component checks are in [summary.json](summary.json). Positive scope is limited to these semantic wizards and this Fable low/Ego configuration. Confidence is not a universal error bound.",'','Exact author-known routes allow deterministic verification, but the app also provides immediate wrong-choice feedback. Real sites usually do not. The tasks omit typing, network races, uploads, logins, payments, canvas, iframes and long planning. No claims about those capabilities follow from this screen.','', 'A suitable candidate integration is a persistent browser subtask executor, with deterministic handling where available, Jev for bounded semantic choices, and explicit escalation. The mixed fallback workflow itself was not measured here. Main-model host dollar estimates omit Jev and are not subscription bills; token counts and call counts are provided without an unsupported total monetary-saving claim.','', 'See [protocol and reproduction](../README.md), [fixtures](../fixture/tasks.json), [all attempts](runs.json), and [primary-source research](../RESEARCH.md).','']
 (a.out/'RESULTS.md').write_text('\n'.join(lines))
if __name__=='__main__':main()
