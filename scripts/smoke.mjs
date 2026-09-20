import assert from 'node:assert/strict';import {readFileSync,writeFileSync} from 'node:fs';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const root=new URL('../',import.meta.url),client=new Client({name:'jev-kit-live-smoke',version:'1.0.0'});
const output=process.argv[2];if(!output)throw Error('Supply a NEW receipt path');
await client.connect(new StdioClientTransport({command:process.execPath,args:[new URL('dist/cli.js',root).pathname,'serve'],env:Object.fromEntries(['TYPESAFE_API_KEY','TYPESAFE_API_KEY_FILE'].filter(k=>process.env[k]).map(k=>[k,process.env[k]])),stderr:'pipe'}));
const results=[];
try{
 const list=await client.listTools();assert.deepEqual(list.tools.map(t=>t.name).sort(),['jev_classify','jev_decide','jev_evidence','jev_extract','jev_rerank']);
 for(const name of ['evidence','classify','extract','decide','rerank']){
  const input=JSON.parse(readFileSync(new URL(`examples/${name}.json`,root)));
  const raw=await client.callTool({name:`jev_${name}`,arguments:input});assert(!raw.isError);
  const body=JSON.parse(raw.content[0].text);assert.equal(body.status,'ok');
  assert(body.calls.every(c=>c.model&&c.model!=='jev-latest'));
  results.push({name,body});
 }
 assert.equal(results[0].body.results[0].relation,'contradicts');
 assert.equal(results[0].body.results[1].relation,'quote_not_found');
 assert.deepEqual(results[1].body.results.map(r=>r.classification),['bug','feature','manual_review']);
 assert(results[1].body.results[2].requires_review);
 assert.equal(results[2].body.results[0].value,'2.1.0');
 assert.equal(results[3].body.results[0].selected,'local');
 assert.deepEqual(results[4].body.selected_ids,['sum']);
 assert.equal(results[4].body.results.length,3);
 writeFileSync(output,JSON.stringify({status:'passed',tools:5,results},null,2),{flag:'wx',mode:0o600});
 console.log('Live MCP smoke passed: evidence, classify, extract, decide, rerank');
}finally{await client.close()}
