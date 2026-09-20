import test from 'node:test';
import assert from 'node:assert/strict';
import {createBackend} from '../src/backend.js';
import {run} from '../src/core.js';

const input={query:'find the relevant implementation',candidates:[
 {id:'wrong',text:'A related but unrelated helper.',source_ref:'private/wrong.js'},
 {id:'right',text:'The exact implementation to inspect.',source_ref:'private/right.js'},
]};

function installFakeKey(t){
 const before=process.env.TYPESAFE_API_KEY;
 process.env.TYPESAFE_API_KEY='test-rerank-key';
 t.after(()=>{if(before===undefined)delete process.env.TYPESAFE_API_KEY;else process.env.TYPESAFE_API_KEY=before;});
 return 'test-rerank-key';
}

function installFetch(t,handler){
 const before=globalThis.fetch;
 globalThis.fetch=handler;
 t.after(()=>{globalThis.fetch=before;});
}

test('score backend maps reverse-order native answer keys back to r0/r1',async t=>{
 const key=installFakeKey(t);let requests=0;
 installFetch(t,async(url,options)=>{
  requests++;
  assert.equal(url,'https://api.typesafe.ai/v1/systemone');
  assert.equal(options.headers.Authorization,`Bearer ${key}`);
  const body=JSON.parse(options.body);
  assert.equal(body.model,'jev-latest');
  assert.deepEqual(Object.keys(body.questions),['r0','r1']);
  assert.equal(body.questions.r0.type,'score');assert.equal(body.questions.r0.criteria.length,4);
  assert.deepEqual(JSON.parse(body.state),{query:input.query,candidates:input.candidates.map(({id,text})=>({id,text}))});
  assert(!body.state.includes('private/'));
  // Deliberately insert r1 first: TypeSafeBackend must reconstruct answers
  // using the request question IDs, not the provider object's key order.
  return new Response(JSON.stringify({model:'jev-1.test',answers:{
   r1:{score:3,probabilities:{0:0,1:0,2:0,3:1}},
   r0:{score:0,probabilities:{0:1,1:0,2:0,3:0}},
  },usage:{input_tokens:11,output_tokens:0}}),{status:200,headers:{'content-type':'application/json'}});
 });
 const result=await run('rerank',input,createBackend('score'));
 assert.equal(requests,1);assert.equal(result.status,'ok');assert.deepEqual(result.results.map(row=>row.id),['right','wrong']);
 assert.deepEqual(result.selected_ids,['right','wrong']);assert.equal(result.calls[0].model,'jev-1.test');
});

test('score backend refuses a credential-bearing payload before fetch',async t=>{
 const key=installFakeKey(t);let requests=0;
 installFetch(t,async()=>{requests++;throw Error('fetch must not run');});
 const result=await run('rerank',{...input,query:`do not send ${key}`},createBackend('score'));
 assert.equal(requests,0);assert.equal(result.status,'partial');assert.equal(result.calls[0].error,'provider_or_validation_error');
 assert(!JSON.stringify(result).includes(key));
});
