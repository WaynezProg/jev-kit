import importlib.util,json,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('model_tier_benchmark',Path(__file__).resolve().parents[1]/'benchmarks/model-tiers/run.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
class ModelTierTests(unittest.TestCase):
 def test_binding_rejects_replaced_claim_even_with_same_source(self):
  items=[{'id':'a','source_text':'original','claim':'claim'}]
  row={'id':'a','source_sha256':t.sha('original'),'claim_sha256':t.sha('claim'),'relation':'supports','requires_review':False}
  self.assertEqual(len(t.bound_rows({'results':[row]},items)),1)
  self.assertEqual(t.bound_rows({'results':[dict(row,claim_sha256='changed')]},items),[])
  self.assertEqual(t.bound_rows({'results':[row,row]},items),[])
 def test_cascade_reviews_uncertainty_and_audits_accepted_items(self):
  items=[{'id':str(i),'source_text':'source','claim':'claim'} for i in range(20)]
  rows=[{'id':v['id'],'source_sha256':t.sha('source'),'claim_sha256':t.sha('claim'),'relation':'supports','requires_review':i==0} for i,v in enumerate(items)]
  accepted,audited=t.projection({'results':rows},items,1)
  self.assertNotIn('0',accepted);self.assertEqual(len(audited),2);self.assertEqual(len(accepted),17)
  self.assertFalse(set(accepted)&audited)
 def test_fixture_and_prompts_do_not_expose_gold(self):
  fixture=json.loads((t.ROOT/'evidence.json').read_text())
  self.assertEqual(len({r['source_text'] for r in fixture['input']['items']}),48)
  self.assertEqual(len({r['id'] for r in fixture['input']['items']}),48)
  for label in t.LABELS:self.assertEqual(sum(r['choice']==label for r in fixture['gold']),16)
  prompt=t.prompt(fixture['input']['items'])
  self.assertNotIn('"gold"',prompt);self.assertNotIn('"rationale"',prompt)
