import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseButtons,validChoice,frozenPlan} from '../benchmarks/browser-loop/run.mjs';
import {keywordPlan,planDecision,validPlan,optionsFor} from '../benchmarks/browser-loop/policies.mjs';
test('browser choices bind only observed enabled refs and labels',()=>{
 const buttons=parseButtons('root\n  button [ref=4]\n    text "Portable monitors"\n  button [ref=9] disabled\n    text "Hidden"');
 assert.deepEqual(buttons,[{id:'ref_4',label:'Portable monitors',ref:'@4'}]);
 assert.equal(validChoice('ref_9',{buttons}),false);assert.equal(validChoice('ref_4',{buttons}),true);assert.equal(validChoice('DONE',{buttons}),false);assert.equal(validChoice('BLOCKED',{buttons}),true);
});
test('cheap baseline normalizes plurals and refuses ambiguous matches',()=>{
 const plan=keywordPlan('Find a keyboard');
 assert.equal(planDecision(plan,{status:'active',prompt:'Department',buttons:[{id:'a',label:'Keyboards'},{id:'b',label:'Mice'}]},new Set()),'a');
 assert.equal(planDecision(plan,{status:'active',prompt:'Department',buttons:[{id:'a',label:'Keyboards'},{id:'b',label:'Keyboards accessories'}]},new Set()),'BLOCKED');
 assert.equal(validPlan({concepts:[{terms:['keyboard','typing device']}]}),true);
 assert.equal(validPlan({concepts:[{terms:['keyboard']}],code:'do something'}),false);
});
test('frozen browser schedule excludes pilot and pairs all four arms',()=>{
 const plan=frozenPlan();assert.equal(plan.trials.length,96);
 const tasks=JSON.parse(readFileSync(new URL('../benchmarks/browser-loop/fixture/tasks.json',import.meta.url)));
 assert.equal(tasks.filter(t=>t.split==='heldout').length,8);
 const heldout=new Set(tasks.filter(t=>t.split==='heldout').map(t=>t.id));assert.ok(plan.trials.every(t=>heldout.has(t.task_id)));
 for(const id of heldout)for(let rep=1;rep<=3;rep++)assert.equal(new Set(plan.trials.filter(t=>t.task_id===id&&t.repeat===rep).map(t=>t.arm)).size,4);
});
