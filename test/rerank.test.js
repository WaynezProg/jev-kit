import test from 'node:test';
import assert from 'node:assert/strict';
import {rerank,validateInput,validatedScores} from '../benchmarks/rerank/rank.mjs';
const input={query:'repair parsing',candidates:[{id:'b',text:'candidate b'},{id:'a',text:'candidate a'}]};
const answer=(p)=>({answer:p.reduce((s,v,i)=>s+i*v,0),distribution:Object.fromEntries(p.map((v,i)=>[i,v]))});
test('batch scores bind IDs; score ties keep original search order',async()=>{
 let seen;
 const r=await rerank(input,{judge:async(req)=>{seen=req;return {model:'jev-1.test',answers:[answer([0,0,0,1]),answer([0,0,0,1])]};}});
 assert.equal(seen.questions.length,2);assert.equal(seen.questions[1].type,'score');assert.deepEqual(r.ranked.map(c=>c.id),['b','a']);
});
test('malformed or missing scores retain every original candidate',async()=>{
 for(const answers of [[answer([0,0,0,1])],[answer([0,0,0,1]),{answer:3,distribution:{0:1,1:0,2:0,3:0}}]]){
  const r=await rerank(input,{judge:async()=>({model:'jev-1.test',answers})});
  assert.equal(r.status,'fallback');assert.deepEqual(r.ranked.map(c=>c.id),['b','a']);
 }
});
test('duplicate IDs and oversized evidence reject before provider call',()=>{
 assert.throws(()=>validateInput({...input,candidates:[input.candidates[0],input.candidates[0]]}));
 assert.throws(()=>validateInput({...input,candidates:[{id:'a',text:'x'.repeat(24001)}]}));
 assert.throws(()=>validatedScores({model:'jev-latest',answers:[]},0));
});
test('rounded probability expectations do not become false provider failures',()=>{
 assert.deepEqual(validatedScores({model:'jev-1.test',answers:[{answer:.28,distribution:{0:.75,1:.25,2:0,3:0}}]},1),[.25]);
 assert.throws(()=>validatedScores({model:'jev-1.test',answers:[{answer:.29,distribution:{0:.75,1:.25,2:0,3:0}}]},1));
 assert.deepEqual(validatedScores({model:'jev-1.test',answers:[{answer:.8,distribution:{0:.22,1:.8,2:0,3:0}}]},1),[.8]);
 assert.throws(()=>validatedScores({model:'jev-1.test',answers:[{answer:.8,distribution:{0:.23,1:.8,2:0,3:0}}]},1));
});
