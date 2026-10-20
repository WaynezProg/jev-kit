import {test} from 'node:test';
import assert from 'node:assert/strict';
import {run,sha} from '../src/core.js';
import {StrictBackend} from '../src/backend.js';
import {MAX_STATE_CHARS} from '../src/batching.js';

const answer=q=>({answer:Object.keys(q.options)[0],confidence:.99,distribution:Object.fromEntries(Object.keys(q.options).map((k,i)=>[k,i===0?1:0]))});
const response=r=>({model:'jev-test',answers:r.questions.map(answer)});

test('independent batches overlap up to four, preserve order and isolate a failed batch',async()=>{
 let active=0,peak=0,calls=0;
 const backend=new StrictBackend({async judge(r){
  calls++;peak=Math.max(peak,++active);
  const first=Number(JSON.parse(r.state).items[0].text);
  // Completion order differs from dispatch order.
  await new Promise(resolve=>setTimeout(resolve,first===0?25:2));active--;
  if(first===16)throw Error('unavailable');
  return response(r);
 }});
 const items=Array.from({length:40},(_,i)=>({id:`id${i}`,text:String(i)}));
 const result=await run('classify',{purpose:'Choose',items,classes:[{id:'a',description:'A'},{id:'b',description:'B'}]},backend);
 assert.equal(peak,4);assert.equal(calls,5);assert.equal(active,0);
 assert.equal(result.status,'partial');assert.deepEqual(result.results.map(r=>r.id),items.map(r=>r.id));
 assert.deepEqual(result.results.map((r,i)=>r.requires_review?i:null).filter(x=>x!==null),[16,17,18,19,20,21,22,23]);
 assert.deepEqual(result.calls.map(r=>!!r.error),[false,false,true,false,false]);
 assert(result.calls.every(r=>r.backend_attempted));
});

test('state budget splits whole sources before one large batch can reject all rows',async()=>{
 const requests=[];
 const backend=new StrictBackend({async judge(r){requests.push(r);return response(r);}});
 const items=Array.from({length:3},(_,i)=>({id:String(i),claim:'This source is available.',source_text:String(i)+'x'.repeat(50000),source_ref:`private:${i}`}));
 const result=await run('evidence',{items},backend);
 assert.equal(requests.length,2);assert(requests.every(r=>r.state.length<=MAX_STATE_CHARS));
 assert.deepEqual(requests.flatMap(r=>JSON.parse(r.state).items.map(i=>i.source_text)),items.map(i=>i.source_text));
 assert.deepEqual(result.results.map(r=>r.source_sha256),items.map(i=>sha(i.source_text)));
 assert.equal(result.results.filter(r=>r.requires_review).length,0);
});

test('shared sources retain exact whitespace and bind each question to its own source',async()=>{
 const sources=[' A passed.\n'+'a'.repeat(2000),' A failed.\n'+'b'.repeat(2000)];
 const items=Array.from({length:8},(_,i)=>({id:String(i),claim:'A passed.',source_text:sources[i%2],source_ref:`private:${i}`}));
 const requests=[];
 const backend=new StrictBackend({async judge(r){
  requests.push(r);const state=JSON.parse(r.state);
  assert.deepEqual(state.sources,sources);
  state.items.forEach((item,i)=>{
   assert.equal(item.source_index,i%2);
   assert(r.questions[i].question.includes(`Use only sources[${i%2}], which is the source assigned to items[${i}]`));
  });
  return response(r);
 }});
 const result=await run('evidence',{items},backend);
 assert.equal(requests.length,1);assert(!requests[0].state.includes('private:'));
 assert.deepEqual(result.results.map(r=>r.source_sha256),items.map(i=>sha(i.source_text)));
 assert.deepEqual(result.results.map(r=>r.source_ref),items.map(i=>i.source_ref));
});

test('an oversized singleton is preserved for review without claiming a model call',async()=>{
 let calls=0;const backend=new StrictBackend({async judge(r){calls++;return response(r);}});
 const source='x'.repeat(80000);
 const result=await run('evidence',{items:[{id:'large',claim:'x',source_text:source,quote:source,source_ref:'local'}]},backend);
 assert.equal(calls,0);assert.equal(result.results[0].review_reason,'oversized');
 assert.equal(result.results[0].source_sha256,sha(source));
 assert.equal(result.calls[0].backend_attempted,false);assert.equal(result.calls[0].model,null);
});
