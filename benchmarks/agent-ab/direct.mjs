// Standalone engine comparison: no host/model review. Not equivalent to the agent arms.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {run} from '../../src/core.js';
const output=process.argv[2];if(!output)throw Error('Supply a new private output directory');
const order=process.argv[3];if(order&&order!=='--agent-order')throw Error('Unknown order option');
const orders=order?JSON.parse(readFileSync(new URL('agent-orders.json',import.meta.url))):null;
mkdirSync(output,{recursive:false,mode:0o700});
for(let repeat=1;repeat<=3;repeat++)for(const name of ['repository-evidence','issue-triage']){
 const fixture=JSON.parse(readFileSync(new URL(name+'.json',import.meta.url)));
 if(orders){
  const ids=orders[repeat][name],byId=new Map(fixture.input.items.map(r=>[r.id,r]));
  if(ids.length!==byId.size||new Set(ids).size!==byId.size||ids.some(id=>!byId.has(id)))throw Error('Invalid frozen agent order');
  fixture.input.items=ids.map(id=>byId.get(id));
 }
 const start=performance.now(),result=await run(fixture.mode,fixture.input),wall_s=(performance.now()-start)/1000;
 const gold=new Map(fixture.gold.map(r=>[r.id,r.choice]));
 const correct=r=>(r.relation??r.classification)===gold.get(r.id);
 const accepted=result.results.filter(r=>!r.requires_review);
 const record={workload:name,repeat,wall_s,status:result.status,correct:result.results.filter(correct).length,total:gold.size,accepted:accepted.length,accepted_correct:accepted.filter(correct).length,review:result.results.length-accepted.length,input_tokens:result.calls.reduce((n,c)=>n+(c.usage.inputTokens??0),0),output_tokens:result.calls.reduce((n,c)=>n+(c.usage.outputTokens??0),0),models:[...new Set(result.calls.map(c=>c.model))],receipt:result};
 record.order=order?'agent-shuffled':'source-grouped';
 record.predictions=result.results.map(r=>({id:r.id,choice:r.relation??r.classification??null,expected:gold.get(r.id),requires_review:r.requires_review}));
 writeFileSync(resolve(output,`${name}-r${repeat}.json`),JSON.stringify(record,null,2),{flag:'wx',mode:0o600});
 console.log(JSON.stringify({workload:name,repeat,wall_s,correct:record.correct,total:record.total,review:record.review}));
}
