import hashlib,importlib.util,json,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('cascade_benchmark',Path(__file__).resolve().parents[1]/'benchmarks/cascade/run.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class CascadeTests(unittest.TestCase):
 def test_rule_escalates_ambiguous_text_and_uses_primary_title(self):
  self.assertEqual(c.rule('Title: OAuth login fails\n\nBody:\nUsing Windows.'),'auth')
  self.assertIsNone(c.rule('Title: MCP auth failure\n\nBody:\nMixed'))
  self.assertIsNone(c.rule('Title: Unexpected behavior\n\nBody:\nNo subsystem evidence.'))
 def test_hash_binding_and_review_flags_prevent_automatic_acceptance(self):
  items=[{'id':'a','text':'original'}]
  row={'id':'a','text_sha256':hashlib.sha256(b'original').hexdigest(),'classification':'mcp','requires_review':False}
  self.assertEqual(c.project({'results':[row]},items),{'a':'mcp'})
  self.assertEqual(c.project({'results':[dict(row,requires_review=True)]},items),{})
  self.assertEqual(c.project({'results':[dict(row,text_sha256='wrong')]},items),{})
  self.assertEqual(c.project({'results':[row,row]},items),{})
 def test_audit_is_stable_and_covers_ten_percent(self):
  ids={str(i):'auth' for i in range(23)}
  self.assertEqual(len(c.audit_ids(ids,1)),3)
  self.assertEqual(c.audit_ids(ids,1),c.audit_ids(dict(reversed(list(ids.items()))),1))
 def test_prompt_hides_reference_labels_and_rejects_missing_or_duplicate_answers(self):
  items=[{'id':'a','text':'public text'},{'id':'b','text':'other text'}]
  self.assertNotIn('"gold"',c.prompt(items));self.assertNotIn('reference',c.prompt(items))
  self.assertTrue(c.answer_map(json.dumps({'decisions':[{'id':'a','choice':'auth'},{'id':'b','choice':'manual_review'}]}),items)[1])
  self.assertFalse(c.answer_map(json.dumps({'decisions':[{'id':'a','choice':'auth'},{'id':'a','choice':'auth'}]}),items)[1])
