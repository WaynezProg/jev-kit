// Native Claude continuation probe; does NOT install or exercise Claude's compact hook.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {ClaudeSession} from '../browser-loop/claude-session.mjs';
const [replay,out]=process.argv.slice(2).map(p=>resolve(p));mkdirSync(out,{recursive:true});
const plan=JSON.parse(readFileSync(join(replay,'plan.json'))),rows=[];
const save=(name,data)=>writeFileSync(join(out,name),JSON.stringify(data,null,2)+'\n',{flag:'wx',mode:0o600});
save('plan.json',{cases:plan.cases.map(c=>c.id),arms:['full','jev','recency'],replay_repeat:1,kind:'Native Claude fact-continuation probe, not coding benchmark or native /compact comparison',model:'claude-fable-5-1',effort:'low'});
for(let i=0;i<plan.cases.length;i++){
 const c=plan.cases[i],r=JSON.parse(readFileSync(join(replay,`${c.id}-1.json`)));
 const arms=['full','jev','recency'];for(const arm of [...arms.slice(i%3),...arms.slice(0,i%3)]){
  const messages=arm==='full'?c.messages:arm==='jev'?r.messages:r.recency_messages;
  const folder=join(out,`${c.id}-${arm}`);mkdirSync(folder);const session=new ClaudeSession(folder),start=performance.now();
  let answer,error=null;
  try{answer=await session.ask(`From the supplied transcript, return ONLY JSON {"facts":["incident identifier","numeric limit token","rejected approach token"]}. Use exact original tokens. Use null for any missing value; do not guess.\n${JSON.stringify(messages)}`);}catch(e){error=e.message;}finally{session.close();}
  const row={id:c.id,arm,seconds:(performance.now()-start)/1000,error,answer,correct:JSON.stringify(answer?.facts)===JSON.stringify(c.gold),input_bytes:Buffer.byteLength(JSON.stringify(messages)),model:[...session.observed],usage:session.lastResult?.usage??null,host_cost_usd:session.lastResult?.total_cost_usd??null};
  rows.push(row);save(`${c.id}-${arm}.json`,row);console.log(JSON.stringify({id:c.id,arm,correct:row.correct,seconds:row.seconds,error}));
  if(error){save('results.json',rows);process.exit(2);}
 }
}
save('results.json',rows);
