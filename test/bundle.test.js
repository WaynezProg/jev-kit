import {test} from 'node:test';import assert from 'node:assert/strict';import {spawnSync} from 'node:child_process';
import {mkdtempSync,copyFileSync,writeFileSync,rmSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';
test('standalone bundle works without node_modules, including regex worker',()=>{
 const dir=mkdtempSync(join(tmpdir(),'jev-kit-bundle-'));try{
  copyFileSync(new URL('../dist/cli.js',import.meta.url),join(dir,'cli.mjs'));
  const d={document:'no numbers here',source_ref:'test',fields:[{id:'number',description:'Number',pattern:'[0-9]+'}]};
  const p=spawnSync(process.execPath,[join(dir,'cli.mjs'),'extract'],{input:JSON.stringify(d),encoding:'utf8',env:{PATH:process.env.PATH,TYPESAFE_API_KEY_FILE:join(dir,'missing-key')}});
  assert.equal(p.status,0,p.stderr);const r=JSON.parse(p.stdout);assert.equal(r.results[0].status,'not_found');assert.equal(r.calls.length,0);
 }finally{rmSync(dir,{recursive:true,force:true})}
});
