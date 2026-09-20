import {readFileSync,openSync,closeSync,unlinkSync,writeFileSync} from 'node:fs';
import {spawn,execFileSync} from 'node:child_process';
import {createInterface} from 'node:readline';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
import {tmpdir} from 'node:os';
export const UPSTREAM_SHA='1231850a0bf1a0c0341fe408ef1668dbbfdfac46';
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function rebindPlannedAction(original,current,id){
 const planned=original.actions.find(a=>a.id===id);
 if(!planned)throw Error('action_not_observed');
 if(!same(original.page_key.slice(0,2),current.page_key.slice(0,2)))throw Error('plan_invalidated');
 // A form edit may change the global page key. Only keep an unused target if
 // its DOM identity AND semantic guard are unchanged; never retarget by label.
 if(!planned.node){if(!same(original.marker,current.marker))throw Error('plan_invalidated');return planned;}
 if(!same(original.guards[planned.node],current.guards[planned.node]))throw Error('plan_invalidated');
 const matches=current.actions.filter(a=>a.node===planned.node&&a.kind===planned.kind&&a.value===planned.value&&a.label===planned.label);
 if(matches.length!==1)throw Error('plan_invalidated');
 return matches[0];
}
export function validatePlan(answer,state){
 const actions=answer.actions??[{choice:answer.choice}];
 if(!Array.isArray(actions)||actions.length<1||actions.length>5)throw Error('invalid_plan');
 const seen=new Set();
 for(const a of actions){
  if(!a||typeof a.choice!=='string'||Object.keys(a).some(k=>!['choice','text'].includes(k)))throw Error('invalid_plan');
  if(['DONE','BLOCKED'].includes(a.choice)){if(actions.length!==1||Object.hasOwn(a,'text'))throw Error('invalid_plan');continue;}
  const target=state.actions.find(t=>t.id===a.choice);
  if(!target||seen.has(a.choice))throw Error('invalid_plan');
  if(Object.hasOwn(a,'text')&&(target.kind!=='fill'||typeof a.text!=='string'||!a.text.trim()||a.text.length>2000))throw Error('invalid_field_text');
  seen.add(a.choice);
 }
 return actions;
}
export function summarizeReceipt(receipt){
 if(!receipt||typeof receipt!=='object')return {observed:false};
 // Never persist dialog messages, page text, target IDs or arbitrary runtime data.
 return {observed:true,popups:(receipt.popups??[]).map(p=>({label:p.label??null})),dialog:!!receipt.dialog,
  executionStopped:receipt.executionStopped??null,mayHaveLateEffects:receipt.mayHaveLateEffects??null};
}
export function isMissingClickTarget(error,selector){
 // Ego's locator timeout means the element never became usable for dispatch.
 // Do not generalize to arbitrary click timeouts or errors with late effects.
 return !error.mayHaveLateEffects&&!error.executionStopped&&
  /^page\.click timed out after \d+ms: Locator /.test(error.message??'')&&
  error.message.endsWith(`Locator ${selector} matched 0 elements`);
}
export function acquirePageLease(page){
 const path=join(tmpdir(),`jev-kit-ego-${page.spaceId}-${page.label}.lock`);
 const fd=openSync(path,'wx',0o600);writeFileSync(fd,JSON.stringify({pid:process.pid,space:page.spaceId,page:page.label}));
 let released=false;return ()=>{if(!released){released=true;closeSync(fd);unlinkSync(path);}};
}
export function checkUpstream(root){
 const sha=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
 if(sha!==UPSTREAM_SHA)throw Error('upstream_revision_mismatch');
 if(execFileSync('git',['-C',root,'status','--porcelain','--','jev_ultrafast'],{encoding:'utf8'}).trim())throw Error('upstream_source_modified');
 return readFileSync(join(root,'jev_ultrafast/snapshot.js'),'utf8');
}
export class UpstreamPolicy {
 constructor(root,python){
  checkUpstream(root);this.waiter=null;
  this.child=spawn(python,[fileURLToPath(new URL('./policy.py',import.meta.url)),root],{stdio:['pipe','pipe','ignore']});
  createInterface({input:this.child.stdout}).on('line',line=>{let data;try{data=JSON.parse(line);}catch{return;}if(this.waiter){const w=this.waiter;this.waiter=null;clearTimeout(w.timer);data.ok?w.resolve(data.result):w.reject(Error(`upstream_${data.error}`));}});
  const fail=()=>{if(this.waiter){clearTimeout(this.waiter.timer);this.waiter.reject(Error('policy_process_stopped'));this.waiter=null;}};
  this.child.on('error',()=>{this.stopped=true;fail();});this.child.on('exit',()=>{this.stopped=true;fail();});
  this.child.on('close',()=>{this.closed=true;});
  this.child.stdin.on('error',()=>{this.stopped=true;fail();});
 }
 request(input){if(this.stopped)throw Error('policy_process_stopped');if(this.waiter)throw Error('overlapping_policy_request');return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.waiter=null;this.close();reject(Error('policy_timeout'));},30000);this.waiter={resolve,reject,timer};this.child.stdin.write(JSON.stringify(input)+'\n');});}
 choose(state,goal,history){return this.request({method:'choose',state,goal,history});}
 text(state,action,goal,history){return this.request({method:'text',state,action,goal,history});}
 async close(){
  if(this.closed)return;
  const stopped=new Promise(resolve=>this.child.once('close',resolve));
  this.child.stdin.end();this.child.kill('SIGTERM');
  const bounded=async ms=>{let timer;try{return await Promise.race([stopped.then(()=>true),new Promise(resolve=>{timer=setTimeout(()=>resolve(false),ms);})]);}finally{clearTimeout(timer);}};
  if(!await bounded(2000)){this.child.kill('SIGKILL');if(!await bounded(1000))throw Error('policy_cleanup_timeout');}
 }
}
export class EgoAdapter {
 constructor(page,{upstream,origins}){this.page=page;this.readState=checkUpstream(upstream);this.origins=new Set(origins);this.token=randomUUID();}
 async observe(){
  await this.page.waitForFunction(()=>!!document.body&&document.readyState!=='loading',undefined,{timeout:10000});
  // Preserve upstream's atomic DOM state and node identity; only replace its executor.
  const state=await this.page.evaluate(`(() => {const state=${this.readState}; if(!state)return null; const token=${JSON.stringify(this.token)}; for(const a of state.actions){if(a.node) window.__jevFast.nodes.get(a.node).setAttribute('data-jev-kit-target',token+':'+a.node);} return state;})()`);
  if(!state)throw Error('page_unavailable');
  if(!this.origins.has(new URL(state.url).origin))throw Error('origin_out_of_scope');
  return state;
 }
 async settle(){
  // As in upstream, a bounded pair of animation frames settles post-input rendering.
  // Navigation may destroy this context; observe() waits for the new document.
  try{await this.page.evaluate(()=>new Promise(resolve=>{const timer=setTimeout(resolve,50);requestAnimationFrame(()=>requestAnimationFrame(()=>{clearTimeout(timer);resolve();}));}));}
  catch(e){if(!/context|navigat/i.test(String(e)))throw e;}
 }
 async act(state,id,text){
  const action=state.actions.find(a=>a.id===id);if(!action)throw Error('action_not_observed');
  const checked=await this.page.evaluate(({state,action,token})=>{
   const c=window.__jevFast;
   if(!c||JSON.stringify(c.pageKey())!==JSON.stringify(state.page_key))return {ok:false};
   if(!action.node)return {ok:true};
   const e=c.nodes.get(action.node);
   if(!e||JSON.stringify(c.guard(e))!==JSON.stringify(state.guards[String(action.node)])||e.getAttribute('data-jev-kit-target')!==token+':'+action.node)return {ok:false};
   if(!e.isConnected||e.matches(':disabled')||e.closest('[aria-disabled="true"],[inert]'))return {ok:false};
   const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;
   if(!r.width||!r.height||!e.contains(document.elementFromPoint(x,y)))return {ok:false};
   if(action.kind==='fill'&&(e.readOnly||e.getAttribute('aria-readonly')==='true'))return {ok:false};
   if(action.kind==='select'&&![...e.options].some(o=>o.value===action.value&&!o.disabled&&!o.closest('optgroup[disabled]')))return {ok:false};
   return {ok:true,href:e.closest('a[href]')?.href??null};
  },{state,action,token:this.token});
  if(!checked.ok)throw Error('stale_or_covered_target');
  if(checked.href&&!this.origins.has(new URL(checked.href).origin))throw Error('navigation_out_of_scope');
  const selector=`loc=css:[data-jev-kit-target="${this.token}:${action.node}"]`;
  let receipt;
  try{
  if(action.kind==='click')receipt=await this.page.click(selector,{label:'Execute selected browser control'});
  else if(action.kind==='fill'){
   if(typeof text!=='string'||!text.trim()||text.length>2000)throw Error('invalid_field_text');
   receipt=await this.page.fill(selector,text);
  }else if(action.kind==='select')receipt=await this.page.selectOption(selector,{value:action.value});
  else if(action.kind==='scroll'){await this.page.mouse.move(Math.floor(state.w/2),Math.floor(state.h/2));receipt=await this.page.mouse.wheel(0,action.delta,{label:'Scroll browser page'});}
  else if(action.kind==='wait'){
   // Bounded, observable state change rather than an unconditional delay.
   const before=await this.page.evaluate(()=>({url:location.href,text:document.body?.innerText,key:window.__jevFast?.pageKey()}));
   try{await this.page.waitForFunction(old=>location.href!==old.url||document.body?.innerText!==old.text||JSON.stringify(window.__jevFast?.pageKey())!==JSON.stringify(old.key),before,{timeout:750});}catch(e){if(!/timeout/i.test(String(e)))throw e;}
  }else throw Error('unsupported_action');
  }catch(e){if(isMissingClickTarget(e,selector))throw Error('target_disappeared_before_dispatch',{cause:e});throw e;}
  return {...action,receipt:summarizeReceipt(receipt)};
 }
 async cleanup(){await this.page.evaluate(token=>{for(const e of document.querySelectorAll('[data-jev-kit-target]'))if(e.getAttribute('data-jev-kit-target')?.startsWith(token+':'))e.removeAttribute('data-jev-kit-target');},this.token);}
}
export async function runBrowser(page,{upstream,policy,url,goal,origins=[new URL(url).origin],maxSteps=16,maxSeconds=180,shouldStop=()=>false,verify,textHelper,onStep=()=>{}}){
 if(!Number.isInteger(maxSteps)||maxSteps<1||maxSteps>60)throw Error('invalid_step_budget');
 if(!Number.isFinite(maxSeconds)||maxSeconds<1||maxSeconds>600)throw Error('invalid_time_budget');
 if(!origins.includes(new URL(url).origin))throw Error('initial_origin_out_of_scope');
 const adapter=new EgoAdapter(page,{upstream,origins}),history=[],steps=[];
 const started=performance.now();let status='step_budget_exhausted',error=null,staleDecisions=0;
 let state,finalUrl=url,unsafeToObserve=false,executedActions=0;
 const checkpoint=()=>{if(shouldStop())throw Error('cancelled');if((performance.now()-started)/1000>=maxSeconds)throw Error('time_budget_exhausted');};
 try{
  checkpoint();
  await page.goto(url);
  // Initial semantic ground truth; subsequent reads use the upstream structured DOM snapshot.
  await page.snapshot();
  state=await adapter.observe();
  for(let i=0;i<maxSteps;i++){
   checkpoint();
   const before=performance.now(),answer=await policy.choose(state,goal,history);
   checkpoint();
   const plan=validatePlan(answer,state),plannedState=state;
   const row={step:i+1,choice:answer.choice??plan[0].choice,operation:answer.operation??null,model:answer.model??null,confidence:answer.confidence??null,usage:answer.usage??null,decision_s:(performance.now()-before)/1000,planned_actions:plan.length,actions:[]};
   steps.push(row);
   if(plan[0].choice==='DONE'){state=await adapter.observe();status=verify&&await verify(page,state)?'verified':'done_unverified';await onStep(row);break;}
   if(plan[0].choice==='BLOCKED'){status='blocked';await onStep(row);break;}
   for(const [index,planned] of plan.entries()){
   checkpoint();
   let action;
   try{action=index===0?state.actions.find(a=>a.id===planned.choice):rebindPlannedAction(plannedState,state,planned.choice);}
   catch(e){if(e.message!=='plan_invalidated')throw e;row.discarded='plan_invalidated';row.discarded_actions=plan.length-index;break;}
   let text=planned.text;
   if(action.kind==='fill'){
    if(!Object.hasOwn(planned,'text')){
     const textStart=performance.now();const value=textHelper?await textHelper(state,action,goal,history):await policy.text(state,action,goal,history);
     text=value.text;row.text_model=value.model??null;row.text_s=(performance.now()-textStart)/1000;row.text_usage=value.usage??null;
    }
   }
   checkpoint();
   const t=performance.now();
   let dispatched;
   try{dispatched=await adapter.act(state,action.id,text);}
   catch(e){
    if(!['stale_or_covered_target','target_disappeared_before_dispatch'].includes(e.message)||++staleDecisions>3)throw e;
    row.discarded=e.message;row.discarded_actions=plan.length-index;state=await adapter.observe();break;
   }
   row.actions.push({choice:action.id,kind:action.kind,receipt:dispatched.receipt});executedActions++;
   const entry={action:action.label,kind:action.kind,text:text??null,page_changed:null};history.push(entry);row.executed=true;
   if(dispatched.receipt.mayHaveLateEffects||dispatched.receipt.executionStopped){unsafeToObserve=true;throw Error('action_execution_uncertain');}
   if(dispatched.receipt.dialog){unsafeToObserve=true;throw Error('dialog_requires_user');}
   if(dispatched.receipt.popups?.length)throw Error('popup_requires_handoff');
   await adapter.settle();const next=await adapter.observe();
   row.browser_s=(row.browser_s??0)+(performance.now()-t)/1000;
   entry.page_changed=JSON.stringify(next.marker)!==JSON.stringify(state.marker);
   state=next;
   }
   await onStep(row);
  }
 }catch(e){error=e.message;status=['cancelled','time_budget_exhausted'].includes(error)?error:'error';if(/control|ownership|inactive|unassigned/i.test(error)||e.mayHaveLateEffects||e.executionStopped)unsafeToObserve=true;}
 finally{finalUrl=state?.url??url;if(!unsafeToObserve){try{finalUrl=await page.url();await adapter.cleanup();}catch{}}}
 return {status,error,verified:status==='verified',seconds:(performance.now()-started)/1000,executed_actions:executedActions,steps,final_url:finalUrl};
}
