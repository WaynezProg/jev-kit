#!/usr/bin/env python3
"""Rehydrate the frozen public issue URLs privately; fail on changed source text."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
manifest=json.loads((ROOT/'corpus-manifest.json').read_text());catalog=json.loads((ROOT/'catalog.json').read_text());records=[]
for item in manifest['records']:
 number=item['url'].rsplit('/',1)[1]
 raw=json.loads(subprocess.check_output(['gh','api',f'repos/openai/codex/issues/{number}'],text=True))
 text='Title: '+raw['title']+'\n\nBody:\n'+(raw['body'] or '')
 assert hashlib.sha256(text.encode()).hexdigest()==item['sha256'],f'Source changed for issue {number}; cannot reproduce the frozen input'
 records.append({'id':item['id'],'text':text,'gold':item['gold'],'url':item['url'],'updated_at':item['updated_at'],'sha256':item['sha256']})
corpus={**catalog,'records':records,'sampling':manifest['sampling'],'reference':manifest['reference']}
serialized=json.dumps(corpus,ensure_ascii=False,indent=2)
assert hashlib.sha256(serialized.encode()).hexdigest()==manifest['input_sha256'],'Serialized corpus mismatch'
with a.out.open('x') as file:file.write(serialized)
a.out.chmod(0o600)
print('Restored and verified',len(records),'records')
