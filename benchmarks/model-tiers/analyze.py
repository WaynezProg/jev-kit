#!/usr/bin/env python3
import argparse,json,statistics
from pathlib import Path
med=statistics.median
ARMS=['haiku_direct','haiku_assisted','fable_direct','fable_cascade']

def summarize(rows):
 groups={}
 for arm in ARMS:
  runs=[r for r in rows if r['arm']==arm]
  groups[arm]={'runs':len(runs),'correct':sum(r['correct'] for r in runs),'total':sum(r['total'] for r in runs),'median_wall_s':med(r['wall_s'] for r in runs),'median_jev_s':med(r['jev_s'] for r in runs),'median_llm_items':med(r['llm_items'] for r in runs),'median_main_input_tokens':med(r['usage']['input'] for r in runs) if all(r['usage'] is not None for r in runs) else None,'median_main_output_tokens':med(r['usage']['output'] for r in runs) if all(r['usage'] is not None for r in runs) else None,'median_main_thinking_tokens':med(r['usage']['reasoning'] for r in runs) if all(r['usage'] is not None and r['usage']['reasoning'] is not None for r in runs) else None,'median_jev_input_tokens':med(r['jev_input_tokens'] for r in runs),'automated_items':sum(r['automated_items'] for r in runs),'automated_errors':sum(r['automated_errors'] for r in runs),'provider_failures':sum(r['provider_failure'] for r in runs),'all_complete':all(r['complete'] for r in runs),'observed_models':sorted({m for r in runs for m in r['observed_models']})}
 by={(r['arm'],r['repeat']):r for r in rows}
 low=groups['haiku_assisted'];base=groups['haiku_direct'];high=groups['fable_cascade'];highbase=groups['fable_direct']
 gain=100*(low['correct']/low['total']-base['correct']/base['total']);saving=1-high['median_wall_s']/highbase['median_wall_s']
 paired=[]
 for direct,assisted in [('haiku_direct','haiku_assisted'),('fable_direct','fable_cascade')]:
  corrections=regressions=0
  for rep in [1,2,3]:
   a={r['id']:r['choice']==r['expected'] for r in by[direct,rep]['predictions']};b={r['id']:r['choice']==r['expected'] for r in by[assisted,rep]['predictions']}
   corrections+=sum(not a[k] and b[k] for k in a);regressions+=sum(a[k] and not b[k] for k in a)
  paired.append({'direct':direct,'intervention':assisted,'corrections_over_case_repeats':corrections,'regressions_over_case_repeats':regressions})
 lower={'gain_at_least_5pp':gain>=5-1e-9,'all_complete':low['all_complete'] and base['all_complete']}
 higher={'aggregate_accuracy_no_regression':high['correct']>=highbase['correct'],'each_repeat_accuracy_no_regression':all(by['fable_cascade',rep]['correct']>=by['fable_direct',rep]['correct'] for rep in [1,2,3]),'median_wall_reduction_at_least_30pct':saving>=.30,'automated_error_rate_at_most_1pct':high['automated_items']>0 and high['automated_errors']/high['automated_items']<=.01,'all_complete':high['all_complete'] and highbase['all_complete']}
 return {'groups':groups,'lower_tier_gain_pp':gain,'higher_tier_wall_reduction_fraction':saving,'lower_tier_gate':{'checks':lower,'pass':all(lower.values())},'higher_tier_gate':{'checks':higher,'pass':all(higher.values())},'paired_outcomes':paired}

def main():
 p=argparse.ArgumentParser();p.add_argument('--raw',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(exist_ok=True,parents=True)
 rows=[json.loads(f.read_text()) for f in sorted(a.raw.glob('*/result.json'))];assert len(rows)==12
 summary=summarize(rows)
 for name,value in [('runs.json',rows),('summary.json',summary),('plan.json',json.loads((a.raw/'plan.json').read_text()))]: (a.out/name).write_text(json.dumps(value,indent=2)+'\n')
 text=['# Model-tier screening results','','48 newly authored source-bound cases, three repeats per path, actual Claude Code and Jev calls. These are 48 distinct examples, not 144 independent examples. Gold labels were authored with explanations before scored calls; they were not independently adjudicated.','','| Path | Correct over repeats | Median wall seconds | Median main input tokens | Median main output tokens | Median thinking tokens | Median records sent to main model |','|---|---:|---:|---:|---:|---:|---:|']
 for arm in ARMS:
  r=summary['groups'][arm];text.append(f"| {arm} | {r['correct']}/{r['total']} | {r['median_wall_s']:.2f} | {r['median_main_input_tokens']} | {r['median_main_output_tokens']} | {r['median_main_thinking_tokens']} | {r['median_llm_items']} |")
 text+=['',f"Lower-tier accuracy gain: **{summary['lower_tier_gain_pp']:.2f} percentage points**. Frozen gate (at least 5 pp plus complete trials): **{'PASS' if summary['lower_tier_gate']['pass'] else 'FAIL'}**.", '',f"Higher-tier median wall reduction: **{100*summary['higher_tier_wall_reduction_fraction']:.1f}%**. Frozen gate (no aggregate or per-repeat quality loss, at least 30% faster, at most 1% observed unreviewed error, complete trials): **{'PASS' if summary['higher_tier_gate']['pass'] else 'FAIL'}**.",'','| Paired comparison | Wrong → correct | Correct → wrong |','|---|---:|---:|']
 for r in summary['paired_outcomes']:text.append(f"| {r['direct']} → {r['intervention']} | {r['corrections_over_case_repeats']} | {r['regressions_over_case_repeats']} |")
 text+=['','Main-model input tokens include cache reads and writes. Thinking tokens are a subset of reported output tokens. Wall times include the Jev process/API and main-model startup/review; one-time fixture preparation is excluded. Host monetary estimates in raw metrics omit Jev and are not subscription bills; this study does not establish total cost savings.','', 'Haiku uses its native default effort; Fable is explicitly set to low effort. Different model families, defaults, cache states and output-generation speeds all affect wall time. Only within-model intervention comparisons estimate the benefit of the tested Jev path.','', 'A passing screening gate would justify independent production validation, not a claim of general coding improvement, security assurance, or a guaranteed 1% error bound. No threshold was tuned from these results. See [protocol](../README.md), [gate components](summary.json), [all runs](runs.json) and [frozen plan](plan.json).','']
 (a.out/'RESULTS.md').write_text('\n'.join(text))
if __name__=='__main__':main()
