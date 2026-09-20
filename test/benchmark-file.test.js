import {test} from 'node:test';import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,readFileSync,rmSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
test('experimental file adapter preserves records and rejects model-supplied paths',async()=>{
 const dir=mkdtempSync(join(tmpdir(),'jev-file-adapter-'));const input=join(dir,'input.json'),trace=join(dir,'trace.jsonl');
 const data={items:[{id:'original',claim:'Finished',source_text:'Not finished',source_ref:'fixture',quote:'Finished'}]};writeFileSync(input,JSON.stringify(data));
 const client=new Client({name:'file-adapter-test',version:'1.0.0'});
 try{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[new URL('../benchmarks/agent-ab/mcp.mjs',import.meta.url).pathname],env:{JEV_BENCH_INPUT:input,JEV_BENCH_MODE:'evidence',JEV_BENCH_TRACE:trace,TYPESAFE_API_KEY_FILE:join(dir,'missing-key')},stderr:'pipe'}));
  const result=await client.callTool({name:'jev_evidence_file',arguments:{}});assert(!result.isError);
  const body=JSON.parse(result.content[0].text);assert.equal(body.results[0].relation,'quote_not_found');assert.equal(body.calls.length,0);
  assert.deepEqual(JSON.parse(readFileSync(trace,'utf8')).input,data);
  const rejected=await client.callTool({name:'jev_evidence_file',arguments:{path:'/unapproved/file'}});assert(rejected.isError);
  assert.equal(readFileSync(trace,'utf8').trim().split('\n').length,1);
 }finally{await client.close();rmSync(dir,{recursive:true,force:true})}
});
