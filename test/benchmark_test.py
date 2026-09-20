import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('agent_bench',Path(__file__).resolve().parents[1]/'benchmarks/agent-ab/run.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class BenchmarkTests(unittest.TestCase):
 def test_gold_not_in_model_prompt_and_inputs_pair_exactly(self):
  for name in b.WORKLOADS:
   f=json.loads((b.ROOT/(name+'.json')).read_text())
   a,x=b.prompt_for(f,'baseline',2);c,y=b.prompt_for(f,'jev',2)
   self.assertEqual(x,y);self.assertNotIn('"gold"',a);self.assertNotIn('"gold"',c)
   self.assertNotEqual(a,c)
 def test_duplicate_missing_and_wrong_answers_are_not_silently_accepted(self):
  f={'gold':[{'id':'a','choice':'supports'},{'id':'b','choice':'contradicts'}]}
  r=b.score(f,{'decisions':[{'id':'a','choice':'supports'},{'id':'a','choice':'supports'}]})
  self.assertFalse(r['schema_valid']);self.assertEqual(r['correct'],0)
  self.assertEqual(b.score(f,None)['correct'],0)
  self.assertEqual(b.score(f,{'decisions':[{'id':'a','choice':'supports'},{'id':'b','choice':'supports'}]})['correct'],1)
  for malformed in [{'decisions':None},{'decisions':[{'id':[],'choice':'supports'}]},{'decisions':[{'id':'a','choice':[]},{'id':'b','choice':'contradicts'}]},{'decisions':[{'id':'a','choice':'supports'},{'id':'b','choice':'contradicts'}],'extra':True}]:
   self.assertFalse(b.score(f,malformed)['schema_valid'])
 def test_usage_cache_normalization_and_muse_missing_usage(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   r=b.parse_log('claude',[{'type':'result','result':'{}','usage':{'input_tokens':2,'cache_read_input_tokens':10,'cache_creation_input_tokens':5,'output_tokens':7}}],p)
   self.assertEqual(r['usage']['input'],17)
   r=b.parse_log('codex',[{'type':'turn.completed','usage':{'input_tokens':17,'cached_input_tokens':10,'output_tokens':7,'reasoning_output_tokens':3}}],p)
   self.assertEqual(r['usage']['input'],17);self.assertEqual(r['usage']['output'],7)
   r=b.parse_log('pi',[{'type':'message_end','message':{'role':'assistant','usage':{'input':2,'cacheRead':10,'cacheWrite':5,'output':7},'content':[]}}],p)
   self.assertEqual(r['usage']['input'],17)
   self.assertIsNone(b.parse_log('muse',[],p)['usage'])
   r=b.parse_log('opencode',[{'type':'step_finish','part':{'tokens':{'input':2,'output':7,'reasoning':3,'cache':{'read':10,'write':5}}}}],p)
   self.assertEqual(r['usage']['input'],17);self.assertEqual(r['usage']['output'],10);self.assertEqual(r['usage']['reasoning'],3)
 def test_plan_counterbalances_order_and_covers_all_cells(self):
  p=b.plan(3);self.assertEqual(len(p['trials']),48)
  first={profile['id']:[] for profile in b.PROFILES}
  for i in range(0,len(p['trials']),2):
   a,c=p['trials'][i:i+2];self.assertEqual(a['profile'],c['profile']);self.assertEqual(a['workload'],c['workload']);self.assertNotEqual(a['arm'],c['arm']);first[a['profile']['id']].append(a['arm'])
  for rows in first.values():self.assertEqual(rows.count('baseline'),3);self.assertEqual(rows.count('jev'),3)
  orders=json.loads((b.ROOT/'agent-orders.json').read_text())
  for rep in range(1,4):
   for name in b.WORKLOADS:
    fixture=json.loads((b.ROOT/(name+'.json')).read_text())
    self.assertEqual(orders[str(rep)][name],[r['id'] for r in b.prompt_for(fixture,'baseline',rep)[1]['items']])
 def test_grok_native_mcp_wrapper_receipt_is_not_lost(self):
  receipt={'tool':'jev_evidence','results':[],'calls':[]}
  wrapped=json.dumps({'type':'MCP','output':{'OkayOutput':json.dumps(receipt)}})
  with tempfile.TemporaryDirectory() as d:
   parsed=b.parse_log('grok',[{'type':'user','message':{'role':'user','content':[{'type':'tool_result','content':wrapped}]}},{'type':'result','result':'{}','usage':{'input_tokens':2,'cache_read_input_tokens':10,'output_tokens':7}}],Path(d))
  self.assertEqual(parsed['native_receipts'],[receipt]);self.assertEqual(parsed['usage']['input'],12)

class PublicationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import sys
  sys.path.insert(0,str(b.ROOT))
  import analyze
  cls.a=analyze
 def test_input_equivalence_allows_order_and_absent_null_quote_but_not_source_mutation(self):
  x={'items':[{'id':'a','source_text':' exact ','quote':None},{'id':'b','source_text':'B'}]}
  y={'items':[{'id':'b','source_text':'B'},{'id':'a','source_text':' exact '}]}
  self.assertTrue(self.a.input_equivalent(x,y,'evidence'))
  y['items'][1]['source_text']='exact'
  self.assertFalse(self.a.input_equivalent(x,y,'evidence'))
 def test_missing_usage_stays_null_and_invalid_labels_are_not_published(self):
  fixture=json.loads((b.ROOT/'repository-evidence.json').read_text())
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory);(p/'input.json').write_text(json.dumps(fixture['input']))
   (p/'result.json').write_text(json.dumps({'id':'test','profile':b.PROFILES[0],'workload':'repository-evidence','repeat':1,'arm':'baseline','wall_s':1,'exit_code':1,'timeout':False}))
   (p/'events.jsonl').write_text(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':json.dumps({'decisions':[{'id':fixture['gold'][0]['id'],'choice':'private diagnostic text'}]})}})+'\n')
   result=self.a.normalize(p,'test')
   self.assertIsNone(result['main_input_tokens']);self.assertFalse(result['main_usage_complete']);self.assertFalse(result['schema_valid'])
   self.assertNotIn('private diagnostic text',json.dumps(result));self.assertEqual(result['correct'],0)
 def test_paired_ratios_do_not_pair_different_repeats(self):
  rows=[]
  for rep,a,c in [(1,10,20),(2,100,110)]:
   for arm,wall in [('baseline',a),('jev',c)]:
    rows.append({'phase':'test','profile':'one','workload':'one','repeat':rep,'arm':arm,'wall_s':wall,'completed':True,'intervention_valid':True,'correct':1,'total':1,'jev_review_items':0,'agent_fixed_jev_errors':0,'agent_introduced_errors':0})
  group=self.a.groups(rows)[0]
  self.assertAlmostEqual(group['paired_median_wall_ratio'],1.55)
  self.assertEqual(group['paired_median_extra_s'],10)
