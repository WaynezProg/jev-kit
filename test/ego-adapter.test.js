import {test} from 'node:test';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {validateJob} from '../integrations/ego-browser/cli.mjs';
import {acquirePageLease,EgoAdapter,rebindPlannedAction,validatePlan,summarizeReceipt,isMissingClickTarget} from '../integrations/ego-browser/adapter.mjs';
const job={upstream:'/checkout',python:'/python',url:'https://example.com',goal:'Read page',expect_text:'Example'};
test('browser jobs require independent checks and bounded executable scope',()=>{
 assert.equal(validateJob(job),job);
 for(const bad of [{...job,expect_text:undefined},{...job,url:'javascript:alert(1)'},{...job,max_steps:100},{...job,max_seconds:Infinity},{...job,space_id:-1},{...job,origins:['https://example.com/path']},{...job,origins:['https://another.example']},{...job,expect_url:'https://another.example'},{...job,api_key:'do-not-send'}])assert.throws(()=>validateJob(bad));
});
const state={page_key:[1,'https://example.com',0],marker:['before'],guards:{9:[9,'button','Submit']},actions:[{id:'e1',node:9,kind:'click',label:'Submit',value:''},{id:'e2',node:3,kind:'fill',label:'Query',value:''}]};
test('batch rebinding survives own form edits but not another document or changed target',()=>{
 const edited={...state,page_key:[1,'https://example.com',1],actions:state.actions.map(a=>({...a,id:a.id+'new'}))};
 assert.equal(rebindPlannedAction(state,edited,'e1').id,'e1new');
 for(const changed of [{...edited,page_key:[2,'https://example.com',1]},{...edited,page_key:[1,'https://example.com/next',1]},{...edited,guards:{9:[9,'button','Delete']}},{...edited,actions:[{...state.actions[0],node:10}]}])assert.throws(()=>rebindPlannedAction(state,changed,'e1'),/plan_invalidated/);
});
test('invalid batch cannot smuggle selectors or mix terminal and executable actions',()=>{
 for(const actions of [[],[{choice:'invented'}],[{choice:'e1',selector:'body'}],[{choice:'e1'},{choice:'e1'}],[{choice:'DONE'},{choice:'e1'}],[{choice:'e1',text:'bad'}],[{choice:'e2',text:null}],Array(6).fill({choice:'e1'})])assert.throws(()=>validatePlan({actions},state));
 assert.equal(validatePlan({actions:[{choice:'e2',text:'test'},{choice:'e1'}]},state).length,2);
});
test('receipts preserve interruption signals without arbitrary browser data',()=>{
 const receipt=summarizeReceipt({dialog:{message:'private'},popups:[{label:'p2',targetId:'private'}],mayHaveLateEffects:true,extra:'private'});
 assert.equal(receipt.dialog,true);assert.equal(receipt.mayHaveLateEffects,true);
 assert.deepEqual(receipt.popups,[{label:'p2'}]);assert.ok(!JSON.stringify(receipt).includes('private'));
});
test('only the exact missing-target locator timeout permits re-observation',()=>{
 const selector='loc=css:[data-jev-kit-target="owned:1"]';
 const error=Error(`page.click timed out after 3000ms: Locator ${selector} matched 0 elements`);
 assert.equal(isMissingClickTarget(error,selector),true);
 assert.equal(isMissingClickTarget(error,selector+'x'),false);
 assert.equal(isMissingClickTarget({...error,message:error.message,mayHaveLateEffects:true},selector),false);
 assert.equal(isMissingClickTarget(Error('page.click timed out after input'),selector),false);
});
test('per-page lease prevents concurrent executors and releases cleanly',()=>{
 const page={spaceId:randomUUID(),label:'p1'},release=acquirePageLease(page);
 try{assert.throws(()=>acquirePageLease(page),{code:'EEXIST'});}finally{release();}
 acquirePageLease(page)();release();
});
test('unobserved model target cannot invoke the browser',async()=>{
 const adapter=Object.create(EgoAdapter.prototype);adapter.page={evaluate:()=>{throw Error('must not execute');}};
 await assert.rejects(adapter.act({actions:[]},'invented'),/action_not_observed/);
});
