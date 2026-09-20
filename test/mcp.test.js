import {test} from 'node:test';import assert from 'node:assert/strict';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {InMemoryTransport} from '@modelcontextprotocol/sdk/inMemory.js';
import {createServer} from '../src/server.js';import {StrictBackend} from '../src/backend.js';
test('MCP exposes five tasks and rejects invalid provider answer',async()=>{
 const b=new StrictBackend({async judge(){return {model:'jev-test',answers:[{answer:'invented',confidence:1,distribution:{supports:1,contradicts:0,insufficient:0}}]};}});
 const server=createServer(b),client=new Client({name:'test',version:'1'}),[a,c]=InMemoryTransport.createLinkedPair();
 await server.connect(a);await client.connect(c);
 try{
  assert.deepEqual((await client.listTools()).tools.map(x=>x.name).sort(),['jev_classify','jev_decide','jev_evidence','jev_extract','jev_rerank']);
  const r=await client.callTool({name:'jev_evidence',arguments:{items:[{id:'a',claim:'done',source_text:'done',source_ref:'log'}]}});
  const body=JSON.parse(r.content[0].text);assert.equal(body.status,'partial');assert.equal(body.results[0].verdict,'review');
  const invalid=await client.callTool({name:'jev_evidence',arguments:{items:[]}});assert.equal(invalid.isError,true);
 }finally{await client.close();await server.close();}
});
test('MCP rerank passes score batches and keeps unselected candidates',async()=>{
 const backend={async judge(req){assert(req.questions.every(q=>q.type==='score'));return {model:'jev-test',answers:[{answer:0,distribution:{0:1,1:0,2:0,3:0}},{answer:3,distribution:{0:0,1:0,2:0,3:1}}]};}};
 const server=createServer(backend),client=new Client({name:'test',version:'1'}),[a,c]=InMemoryTransport.createLinkedPair();
 await server.connect(a);await client.connect(c);
 try{
  const input={query:'sum',candidates:[{id:'sort',text:'sorted(xs)'},{id:'sum',text:'sum(xs)'}],top_k:1};
  const raw=await client.callTool({name:'jev_rerank',arguments:input});assert(!raw.isError);
  const body=JSON.parse(raw.content[0].text);assert.equal(body.status,'ok');assert.deepEqual(body.selected_ids,['sum']);assert.deepEqual(body.remaining_ids,['sort']);
  for(const invalid of [{...input,extra:true},{...input,top_k:3}])assert.equal((await client.callTool({name:'jev_rerank',arguments:invalid})).isError,true);
 }finally{await client.close();await server.close();}
});
