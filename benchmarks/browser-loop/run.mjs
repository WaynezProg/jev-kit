import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {ClaudeSession} from './claude-session.mjs';
import {jevDecision,stepPrompt,planPrompt,validPlan,keywordPlan,planDecision,optionsFor} from './policies.mjs';
const ROOT=dirname(fileURLToPath(import.meta.url));
const ARMS=['keywords','llm_plan','llm_step','jev_step'];
const save=(p,v)=>writeFileSync(p,JSON.stringify(v,null,2)+'\n',{mode:0o600,flag:'wx'});
export function parseButtons(snapshot){
 const rows=snapshot.split('\n');const result=[];
 for(let i=0;i<rows.length;i++){
  const match=rows[i].match(/^\s*button(?:\s+"([^"]*)")?\s+\[ref=(\d+)\]/);
  if(!match||/disabled/.test(rows[i]))continue;
  let label=match[1];
  if(!label){const next=rows[i+1]?.match(/^\s*text\s+(".*")\s*$/);if(next){try{label=JSON.parse(next[1]);}catch{}}}
  if(label)result.push({id:`ref_${match[2]}`,label,ref:`@${match[2]}`});
 }
 return result;
}
async function observe(page,failed){
 const snapshot=await page.snapshot();
 const metadata=await page.evaluate(()=>({status:document.body.dataset.state,prompt:document.querySelector('[data-prompt]')?.textContent??'',message:document.querySelector('#message')?.textContent??'',selected:[...document.querySelectorAll('#selection li')].map(x=>x.textContent)}));
 const buttons=parseButtons(snapshot);
 return {...metadata,buttons:buttons.map(({id,label})=>({id,label})),failed_choices:[...failed],_refs:buttons,_snapshot:snapshot};
}
function visible(observation){const {_refs,_snapshot,...state}=observation;return state;}
export function validChoice(choice,state){return typeof choice==='string'&&Object.hasOwn(optionsFor(state),choice);}
export function frozenPlan(split='heldout',repeats=3){
 const bytes=readFileSync(join(ROOT,'fixture/tasks.json'));const tasks=JSON.parse(bytes).filter(t=>t.split===split);
 const trials=[];
 for(let repeat=1;repeat<=repeats;repeat++)for(let i=0;i<tasks.length;i++){
  const shift=(i+repeat-1)%4;const arms=[...ARMS.slice(shift),...ARMS.slice(0,shift)];
  for(const arm of arms)trials.push({id:`${tasks[i].id}-r${repeat}-${arm}`,task_id:tasks[i].id,repeat,arm});
 }
 return {fixture_sha256:createHash('sha256').update(bytes).digest('hex'),split,repeats,trials,models:{llm:'claude-fable-5-1',effort:'low',jev:'jev-latest'},policy:{confidence_threshold:.8,max_decisions:12,history_window:6,completion:'Deterministic application marker plus independent exact selected-path verification; all arms use identical completion check'},criteria:{completed_tasks:'At least as many as each comparator',all_complete_for_positive_claim:true,median_wall_reduction_vs_llm_step:.30,median_wall_reduction_vs_llm_plan:.20},design:'Authored local browser wizard, one real Ego Lite page, serial trials, four arms, same visible DOM and executor. Initial navigation and initial observation excluded; all decisions, planner work, native process startup, later observations and final verification included. Model outcomes on pilot do not enter scored runs. Native CLI session is persistent within a task; Jev gets explicit recent history. Keywords and plan matching can abstain; abstentions are unresolved, not wrong clicks.'};
}
export async function runStudy(page,{out,baseUrl,split='heldout',repeats=3,planOnly=false}){
 out=resolve(out);mkdirSync(out,{recursive:true,mode:0o700});const plan=frozenPlan(split,repeats);
 if(existsSync(join(out,'plan.json'))){if(JSON.stringify(JSON.parse(readFileSync(join(out,'plan.json'))))!==JSON.stringify(plan))throw Error('frozen_plan_changed');}else save(join(out,'plan.json'),plan);
 if(planOnly){console.log(JSON.stringify({frozen:plan.trials.length,sha256:plan.fixture_sha256}));return;}
 const tasks=JSON.parse(readFileSync(join(ROOT,'fixture/tasks.json')));
 for(const trial of plan.trials){
  const folder=join(out,trial.id);if(existsSync(join(folder,'result.json')))continue;mkdirSync(folder,{mode:0o700});
  const task=tasks.find(t=>t.id===trial.task_id);await page.goto(`${baseUrl}/?task=${encodeURIComponent(task.id)}`);await page.waitForSelector('[data-option]');
  const failed=new Set(),history=[],calls=[];let observation=await observe(page,failed);const start=performance.now();
  let session=null,compiled=null,error=null,outcome='budget_exhausted',wrongClicks=0,browserS=0,decisionS=0,plannerS=0,steps=0;
  try{
   if(trial.arm.startsWith('llm_'))session=new ClaudeSession(folder);
   if(trial.arm==='llm_plan'){
    const before=performance.now();compiled=await session.ask(planPrompt(task.goal,visible(observation)));plannerS=(performance.now()-before)/1000;
    if(!validPlan(compiled))throw Error('invalid_plan');save(join(folder,'compiled-plan.json'),compiled);
   }else if(trial.arm==='keywords')compiled=keywordPlan(task.goal);
   for(let n=0;n<12;n++){
    if(observation.status==='done'){outcome='completion_observed';break;}
    const state=visible(observation),before=performance.now();let answer;
    if(trial.arm==='jev_step')answer=await jevDecision(task.goal,state,history);
    else if(trial.arm==='llm_step'){
     const value=await session.ask(stepPrompt(task.goal,state,history));
     if(!value||Object.keys(value).length!==1||!Object.hasOwn(value,'choice'))throw Error('invalid_decision_schema');answer=value;
    }else answer={choice:planDecision(compiled,state,failed)};
    const seconds=(performance.now()-before)/1000;decisionS+=seconds;
    calls.push({state,answer,seconds});
    if(!validChoice(answer.choice,state))throw Error('invalid_action');
    if(answer.choice==='BLOCKED'){outcome=answer.review?'uncertain':'blocked';break;}
    const target=observation._refs.find(b=>b.id===answer.choice);
    const actStart=performance.now();await page.click(target.ref);steps++;
    const next=await observe(page,failed);browserS+=(performance.now()-actStart)/1000;
    const entry={prompt:state.prompt,chosen_label:target.label,outcome:next.status};history.push(entry);
    if(next.status==='error'&&state.status!=='error'){wrongClicks++;failed.add(`${state.prompt}|${target.label}`);next.failed_choices=[...failed];}
    observation=next;
   }
   if(observation.status==='done')outcome='completion_observed';
  }catch(e){error=String(e.message??e);outcome='error';}
  const verification=await page.evaluate(()=>({task_id:window.fixtureState?.taskId,stage:window.fixtureState?.stage,selected:window.fixtureState?.selected,status:document.body.dataset.state}));
  const expected=task.stages.map(s=>s.correct_id);
  const success=outcome==='completion_observed'&&verification.task_id===task.id&&verification.status==='done'&&JSON.stringify(verification.selected)===JSON.stringify(expected);
  const wallS=(performance.now()-start)/1000;
  const native=session?.lastResult??null;
  const result={...trial,success,outcome,error,wall_s:wallS,planner_s:plannerS,decision_s:decisionS,browser_s:browserS,steps,wrong_clicks:wrongClicks,main_calls:session?.turns??0,main_models:[...session?.observed??[]],native_duration_api_ms:native?.duration_api_ms??null,native_usage:native?.usage??null,native_host_cost_estimate_usd:native?.total_cost_usd??null,jev_calls:trial.arm==='jev_step'?calls.length:0,jev_models:[...new Set(calls.map(c=>c.answer.model).filter(Boolean))],jev_input_tokens:calls.reduce((n,c)=>n+(c.answer.usage?.inputTokens??0),0),jev_output_tokens:calls.reduce((n,c)=>n+(c.answer.usage?.outputTokens??0),0),selected:verification.selected??[],expected,decisions:calls.map(c=>({choice:c.answer.choice,raw_choice:c.answer.raw_choice??null,review:c.answer.review??false,confidence:c.answer.confidence??null,seconds:c.seconds,prompt:c.state.prompt,chosen_label:c.state.buttons.find(b=>b.id===c.answer.choice)?.label??null}))};
  session?.close();save(join(folder,'trace.json'),{goal:task.goal,calls,verification});save(join(folder,'result.json'),result);
  console.log(JSON.stringify({id:trial.id,success,outcome,wall_s:wallS,steps,wrong_clicks:wrongClicks,main_calls:result.main_calls,jev_calls:result.jev_calls}));
 }
}
