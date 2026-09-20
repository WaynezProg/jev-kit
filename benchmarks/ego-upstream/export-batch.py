"""Export a completed Ego study without prompts, field text, URLs or local paths."""
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(__file__).resolve().parent / 'results'
prefix = source.name
if prefix not in ['ego-v5', 'ego-v6']:
    raise ValueError('Unknown study version')
load = lambda p: json.loads(p.read_text())
select = lambda d, keys: {k: d[k] for k in keys if k in d}

def save(name, data):
    (target / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def step(s):
    row = select(s, ['step', 'choice', 'operation', 'model', 'confidence', 'usage',
        'decision_s', 'planned_actions', 'text_model', 'text_s', 'text_usage',
        'executed', 'browser_s', 'discarded', 'discarded_actions'])
    row['actions'] = [{**select(a, ['choice', 'kind']), 'receipt':
        select(a.get('receipt', {}), ['observed', 'popups', 'dialog',
            'executionStopped', 'mayHaveLateEffects'])} for a in s.get('actions', [])]
    return row

def result(r):
    row = select(r, ['id', 'repeat', 'arm', 'cohort', 'status', 'verified',
        'seconds', 'total_seconds', 'executed_actions', 'claude_turns',
        'claude_host_cost_usd', 'claude_usage'])
    error = r.get('error')
    safe = {'cancelled', 'time_budget_exhausted', 'stale_or_covered_target',
        'origin_out_of_scope', 'popup_requires_handoff', 'dialog_requires_user',
        'action_execution_uncertain', 'invalid_plan', 'invalid_field_text'}
    row['error_category'] = error if error in safe else 'target_disappeared' if error and 'matched 0 elements' in error else 'runtime_error' if error else None
    row['steps'] = [step(s) for s in r.get('steps', [])]
    return row

raw = load(source / 'batch/results.json')
plan = load(source / 'batch/plan.json')
if len(raw) != len(plan['trials']):
    raise ValueError('Study incomplete; retain failures and finish every planned attempt')
save(f'{prefix}.json', [result(r) for r in raw])
save(f'{prefix}-plan.json', plan)
save(f'{prefix}-summary.json', load(source / 'batch/summary.json'))
save(f'{prefix}-environment.json', load(source / 'environment.json'))
if (source / 'guards.json').exists():
    save(f'{prefix}-guards.json', [{**select(r, ['name', 'pass']),
        **({'result': result(r['result'])} if 'result' in r else {})}
        for r in load(source / 'guards.json')])
if (source / 'dispatch-race.json').exists():
    race = load(source / 'dispatch-race.json')
    save('ego-dispatch-race.json', {**select(race, ['case', 'pass', 'decisions']),
        'result': result(race['result'])})
print(f'Exported {len(raw)} attempts and guard checks')
