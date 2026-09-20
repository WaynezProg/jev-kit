import {test} from 'node:test';import assert from 'node:assert/strict';import {spawnSync} from 'node:child_process';
import {mkdtempSync,readFileSync,writeFileSync,rmSync,statSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';
const cli=new URL('../src/cli.js',import.meta.url).pathname;
test('CLI no-key review and receipt refusal preserve existing files',()=>{
 const dir=mkdtempSync(join(tmpdir(),'jev-kit-')),input=join(dir,'in.json'),output=join(dir,'out.json');
 const env={PATH:process.env.PATH,TYPESAFE_API_KEY_FILE:join(dir,'missing-key')};
 try{
  writeFileSync(input,JSON.stringify({items:[{id:'a',claim:'Done',source_text:'Done',source_ref:'log'}]}));
  const r=spawnSync(process.execPath,[cli,'evidence','--input',input,'--output',output],{env,encoding:'utf8'});assert.equal(r.status,2);assert.equal(JSON.parse(readFileSync(output)).results[0].verdict,'review');assert.equal(statSync(output).mode&0o777,0o600);
  const old=readFileSync(output,'utf8');const r2=spawnSync(process.execPath,[cli,'evidence','--input',input,'--output',output],{env,encoding:'utf8'});assert.equal(r2.status,2);assert(r2.stderr.includes('output_exists'));assert.equal(readFileSync(output,'utf8'),old);
  const r3=spawnSync(process.execPath,[cli,'evidence','--input',input,'--validate-only'],{env,encoding:'utf8'});assert.equal(r3.status,0);assert.equal(JSON.parse(r3.stdout).network_calls,0);
 }finally{rmSync(dir,{recursive:true,force:true})}
});
