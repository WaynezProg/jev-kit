import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {runRerank,validateRerankInput,validateScores} from '../src/rerank.js';

const sha=value=>createHash('sha256').update(value).digest('hex');
const input={query:'repair parsing',candidates:[{id:'b',text:'first source',source_ref:'src/b.js'},{id:'a',text:'second source',source_ref:'src/a.js'}]};
const answer=distribution=>({answer:distribution.reduce((sum,value,index)=>sum+index*value,0),distribution:Object.fromEntries(distribution.map((value,index)=>[index,value]))});

test('one batch binds supplied candidate text and returns all source-bound IDs',async()=>{
 let request;
 const result=await runRerank(input,{judge:async value=>{request=value;return {model:'jev-1.test',answers:[answer([0,0,1,0]),answer([0,0,0,1])],usage:{inputTokens:7,providerSecret:'nope'}};}});
 assert.equal(request.questions.length,2);assert(request.questions.every(question=>question.type==='score'));
 const state=JSON.parse(request.state);assert.deepEqual(state,{query:input.query,candidates:input.candidates.map(({id,text})=>({id,text}))});
 assert(!request.state.includes('src/b.js'));
 assert.deepEqual(result.results.map(row=>row.id),['a','b']);assert.deepEqual(result.selected_ids,['a','b']);
 assert.equal(result.results[0].source_ref,'src/a.js');assert.equal(result.results[0].text_sha256,sha('second source'));
 assert.equal(result.query_sha256,sha(input.query));assert.deepEqual(result.calls[0].usage,{inputTokens:7});
});

test('failure preserves original order and every candidate without provider details',async()=>{
 const result=await runRerank({...input,top_k:1},{judge:async()=>{throw Error('provider secret body');}});
 assert.equal(result.status,'partial');assert.equal(result.method,'original_order_fallback');
 assert.deepEqual(result.results.map(row=>row.id),['b','a']);assert.deepEqual(result.selected_ids,['b']);
 assert(result.results.every(row=>row.score===null&&row.requires_review));assert(!JSON.stringify(result).includes('secret'));
});

test('invalid score and distributions fall back without losing candidates',async()=>{
 const invalid=[
  {model:'jev-1.test',answers:[{answer:NaN,distribution:{0:1,1:0,2:0,3:0}},answer([0,0,0,1])]},
  {model:'jev-1.test',answers:[{answer:2,distribution:{0:.4,1:.4,2:.4,3:0}},answer([0,0,0,1])]},
  {model:'jev-1.test',answers:[{answer:3,distribution:{0:1,1:0,2:0,3:0}},answer([0,0,0,1])]},
 ];
 for(const response of invalid){const result=await runRerank(input,{judge:async()=>response});assert.equal(result.status,'partial');assert.deepEqual(result.results.map(row=>row.id),['b','a']);}
});

test('rounded expectation boundary is accepted only within stated tolerance',()=>{
 assert.deepEqual(validateScores({model:'jev-1.test',answers:[{answer:.285,distribution:{0:.75,1:.25,2:0,3:0}}]},1),[.25]);
 assert.throws(()=>validateScores({model:'jev-1.test',answers:[{answer:.286,distribution:{0:.75,1:.25,2:0,3:0}}]},1));
 assert.deepEqual(validateScores({model:'jev-1.test',answers:[{answer:.8,distribution:{0:.22,1:.8,2:0,3:0}}]},1),[.8]);
 assert.throws(()=>validateScores({model:'jev-1.test',answers:[{answer:.8,distribution:{0:.23,1:.8,2:0,3:0}}]},1));
});

test('equal expected scores retain original search order',async()=>{
 const result=await runRerank(input,{judge:async()=>({model:'jev-1.test',answers:[answer([0,0,0,1]),answer([0,0,0,1])]})});
 assert.deepEqual(result.results.map(row=>row.id),['b','a']);assert.deepEqual(result.results.map(row=>row.original_rank),[1,2]);
});

test('single candidate does not invoke backend or claim a score',async()=>{
 let calls=0;const result=await runRerank({query:'one',candidates:[{id:'only',text:'source'}]},{judge:async()=>{calls++;throw Error('should not run');}});
 assert.equal(calls,0);assert.equal(result.status,'ok');assert.equal(result.method,'single_candidate');assert.equal(result.results[0].score,null);assert.equal(result.results[0].requires_review,false);
});

test('invalid or oversized input rejects before backend is reachable',async()=>{
 let calls=0;const backend={judge:async()=>{calls++;return {};}};
 assert.throws(()=>validateRerankInput({...input,candidates:[input.candidates[0],input.candidates[0]]}));
 assert.throws(()=>validateRerankInput({query:'q',candidates:[{id:'a',text:'x'.repeat(24001)}]}));
 assert.throws(()=>validateRerankInput({query:'q',candidates:[
  {id:'a',text:'你'.repeat(24000)},{id:'b',text:'你'.repeat(24000)},{id:'c',text:'你'.repeat(24000)},
 ]}));
 await assert.rejects(()=>runRerank({query:'',candidates:input.candidates},backend));assert.equal(calls,0);
});
