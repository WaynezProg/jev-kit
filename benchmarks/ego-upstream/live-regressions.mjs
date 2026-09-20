import {createServer} from 'node:http';
import {writeFileSync} from 'node:fs';
import {runBrowser,EgoAdapter,acquirePageLease} from '../../integrations/ego-browser/adapter.mjs';
export async function runRegressions(page,{upstream,output}){
 const server=createServer((req,res)=>{res.setHeader('content-type','text/html');res.end('<!doctype html><title>Guard fixture</title><h1>Initial</h1><form onsubmit="event.preventDefault();document.querySelector(\'h1\').textContent=\'Complete\'"><label>Query<input name="q"></label><label>Delivery<select><option>A</option><option>B</option></select></label><button>Submit</button></form><a href="/popup" target="_blank">Popup</a>');});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const url=`http://127.0.0.1:${server.address().port}`;
 const release=acquirePageLease(page),results=[];
 const record=(name,pass,result)=>{results.push({name,pass,result});};
 const run=(policy,options={})=>runBrowser(page,{upstream,url,goal:'Exercise executor',policy,maxSteps:4,verify:async(_,state)=>state.text.includes('Complete'),...options});
 try{
  let calls=0;
  const batch=await run({choose:async state=>++calls===1?{actions:[{choice:state.actions.find(a=>a.kind==='fill').id,text:'test'},{choice:state.actions.find(a=>a.kind==='select').id},{choice:state.actions.find(a=>a.label==='Submit').id}]}:{choice:'DONE'}});
  record('batch_rebind_after_own_form_edits',batch.verified&&batch.executed_actions===3,batch);
  const fresh=await run({choose:async()=>{await page.evaluate(()=>document.querySelector('h1').textContent='Complete');return {choice:'DONE'};}});
  record('done_observes_fresh_state',fresh.verified,fresh);
  const escape=await run({choose:async()=>{await page.goto('https://example.com/');return {choice:'DONE'};}});
  record('done_rejects_changed_origin',escape.error==='origin_out_of_scope'&&escape.final_url==='https://example.com/',escape);
  let stop=false;
  const cancelled=await run({choose:async state=>{stop=true;return {choice:state.actions.find(a=>a.kind==='fill').id};}},{shouldStop:()=>stop});
  record('cancel_before_input',cancelled.status==='cancelled'&&cancelled.executed_actions===0,cancelled);
  const budget=await run({choose:async()=>{await new Promise(resolve=>setTimeout(resolve,1050));return {choice:'DONE'};}},{maxSeconds:1});
  record('time_budget_before_dispatch',budget.status==='time_budget_exhausted'&&budget.executed_actions===0,budget);
  await page.goto(url);await page.snapshot();const adapter=new EgoAdapter(page,{upstream,origins:[url]});
  let state=await adapter.observe(),button=state.actions.find(a=>a.label==='Submit');
  await page.evaluate(()=>{const e=document.querySelector('button');e.replaceWith(e.cloneNode(true));});
  try{await adapter.act(state,button.id);record('replaced_identity',false);}catch(e){record('replaced_identity',e.message==='stale_or_covered_target');}
  state=await adapter.observe();button=state.actions.find(a=>a.label==='Submit');
  await page.evaluate(()=>{const e=document.createElement('div');e.style='position:fixed;inset:0;background:white;z-index:100';document.body.append(e);});
  try{await adapter.act(state,button.id);record('covered_target',false);}catch(e){record('covered_target',e.message==='stale_or_covered_target');}
  await adapter.cleanup();
  // Last case leaves its observed popup for the caller's TaskSpace lifecycle.
  const popup=await run({choose:async state=>({choice:state.actions.find(a=>a.label==='Popup').id})});
  record('popup_stops_loop',popup.error==='popup_requires_handoff'&&popup.executed_actions===1,popup);
  writeFileSync(output,JSON.stringify(results,null,2)+'\n',{flag:'wx',mode:0o600});return results.map(({name,pass})=>({name,pass}));
 }finally{server.close();server.closeAllConnections();release();}
}
