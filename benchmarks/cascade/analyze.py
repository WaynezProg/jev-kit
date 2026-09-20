#!/usr/bin/env python3
"""Publish metrics only. Issue bodies and native transcripts remain private."""
import argparse,json,statistics
from pathlib import Path
med=statistics.median

def summarize(rows):
 groups={}
 for r in rows:groups.setdefault((r['profile']['id'],r['arm']),[]).append(r)
 result=[]
 for (profile,arm),runs in groups.items():
  result.append({'profile':profile,'arm':arm,'runs':len(runs),'reference_agreement':sum(r['reference_agreement'] for r in runs),'total':sum(r['total'] for r in runs),'median_wall_s':med(r['wall_s'] for r in runs),'median_main_input_tokens':med(r['main_input_tokens'] for r in runs) if all(r['main_input_tokens'] is not None for r in runs) else None,'median_llm_items':med(r['llm_items'] for r in runs),'automated_items':sum(r['automated_items'] for r in runs),'automated_disagreements':sum(r['automated_disagreements'] for r in runs),'all_complete':all(r['complete'] for r in runs),'provider_failures':sum(r['provider_failure'] for r in runs)})
 gates=[]
 for r in result:
  if r['arm'] not in ['jev_llm','rules_jev_llm']:continue
  baselines=[s for s in result if s['profile']==r['profile'] and s['arm'] in ['llm_all','rules_llm']]
  checks={'reference_agreement':all(r['reference_agreement']>=b['reference_agreement'] for b in baselines),'wall_reduction_30pct_vs_both':all(r['median_wall_s']<=.7*b['median_wall_s'] for b in baselines),'input_reduction_50pct_vs_both':all(r['median_main_input_tokens'] is not None and b['median_main_input_tokens'] is not None and r['median_main_input_tokens']<=.5*b['median_main_input_tokens'] for b in baselines),'unreviewed_disagreement_le_1pct':r['automated_items']>0 and r['automated_disagreements']/r['automated_items']<=.01,'all_complete':r['all_complete']}
  gates.append({'profile':r['profile'],'arm':r['arm'],'checks':checks,'pass':all(checks.values())})
 return {'groups':result,'gates':gates}

def main():
 p=argparse.ArgumentParser();p.add_argument('--raw',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(exist_ok=True,parents=True)
 rows=[json.loads(f.read_text()) for f in sorted(a.raw.glob('*/result.json'))];assert len(rows)==24
 summary=summarize(rows)
 for name,data in [('runs.json',rows),('summary.json',summary),('plan.json',json.loads((a.raw/'plan.json').read_text()))]: (a.out/name).write_text(json.dumps(data,indent=2)+'\n')
 text=['# Real-issue cascade screening','','**These are matches to existing GitHub labels, not decision accuracy.** The catalog asks for the main subsystem; repository tags may instead describe environment or overlapping concerns. A correct abstention can therefore disagree with a reference tag. Do not compare model intelligence from these scores.','','All 24 runs completed, including fallback review after one provider/validation failure among 60 Jev API calls. Successful calls resolved to jev-1.13.0; the failed call retained the requested jev-latest alias. No Jev arm met its entire frozen gate against both the direct-LLM and rules-first baselines.','','| Model | Path | Reference matches | Median seconds | Median LLM items | Median main input tokens | Unreviewed disagreements |','|---|---|---:|---:|---:|---:|---:|']
 for r in summary['groups']:text.append(f"| {r['profile']} | {r['arm']} | {r['reference_agreement']}/{r['total']} | {r['median_wall_s']:.2f} | {r['median_llm_items']} | {r['median_main_input_tokens']} | {r['automated_disagreements']}/{r['automated_items']} |")
 text+=['','Three repeats of the same 64 records are not 192 independent examples. Rules-first and hybrid paths retained some disagreements without review; confidence and audit sampling are not error guarantees. The labels were not changed after inspecting results. Full gate components are in [summary.json](summary.json).','']
 (a.out/'RESULTS.md').write_text('\n'.join(text))
if __name__=='__main__':main()
