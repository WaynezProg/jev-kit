#!/usr/bin/env python3
"""Recheck published authored-fixture patches with no model calls."""
import importlib.util,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('runner',ROOT/'run.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
tasks={t['id']:t for t in json.loads((ROOT/'fixture/tasks.json').read_text())}
corpus={c['id']:c for c in json.loads((ROOT/'fixture/corpus.json').read_text())}
patches=json.loads((ROOT/'results/patches.json').read_text())
receipts={r['id']:r for r in json.loads((ROOT/'results/runs.json').read_text())['coding']}
for p in patches:
 receipt=receipts[p['id']]
 if p['candidate_id'] not in receipt['selected_ids'] or not isinstance(p['replacement'],str) or not receipt['main']['complete']:
  if p['passed']:raise RuntimeError(f'invalid patch marked passed: {p["id"]}')
  continue
 with tempfile.TemporaryDirectory() as folder:
  result=runner.check_patch(tasks[p['task']],corpus[p['candidate_id']],p['replacement'],Path(folder))
  if result['passed']!=p['passed']:raise RuntimeError(f'patch replay differs: {p["id"]}')
print(f'Replayed {len(patches)} authored-fixture patches; all outcomes match.')
