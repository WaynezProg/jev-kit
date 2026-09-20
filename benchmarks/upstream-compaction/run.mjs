// Runs the unmodified upstream library on synthetic transcripts. No host hooks installed.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const [upstream,out]=process.argv.slice(2).map(p=>resolve(p));
if(!upstream||!out)throw Error('usage: node run.mjs UPSTREAM OUTPUT');
mkdirSync(out,{recursive:true});
const {compact,JevClient,collectToolCalls,applyDecisions}=await import(pathToFileURL(join(upstream,'dist/index.js')));
const save=(name,data)=>writeFileSync(join(out,name),JSON.stringify(data,null,2)+'\n',{flag:'wx',mode:0o600});
const names=['migration','parser','cache','retry','unicode','pagination'];
const cases=names.map((name,i)=>{
 const gold=[`INCIDENT_${name.toUpperCase()}_${317+i}`,`LIMIT_${71+i}`,`REJECT_${name.toUpperCase()}_V1`];
 const goal=`Continue fixing ${name}. Preserve the incident identifier, exact numeric limit, and rejected approach found in earlier diagnostic output. These observations were from a removed temporary reproduction and cannot be rerun. Latest tests are not the final acceptance check.`;
 const messages=[{role:'user',text:goal+' Do not change the public API.',toolUses:[]}];
 for(let n=0;n<14;n++){
  const critical=[1,4,8].indexOf(n),id=`call_${n}`;
  const text=(`Diagnostic ${name}, record ${n}: routine progress data.\n`).repeat(30)+(critical>=0?`Required observation: ${gold[critical]}\n`:'No new findings.\n')+('background details\n').repeat(8);
  // Alternate self-describing and opaque tool inputs: output itself is omitted from Jev state.
  const input={command:critical>=0&&i%2===0?`read-once-${['incident','limit','rejected-approach'][critical]}-diagnostic`:`read diagnostic chunk ${n}`};
  messages.push({role:'assistant',text:n===6?'The implementation is still in progress.':'',toolUses:[{tool_use_id:id,tool:'Bash',input,text,isError:n===8}]});
  messages.push({role:'user',text:'',toolUses:[],toolResults:[{tool_use_id:id,text,isError:n===8}]});
 }
 messages.push({role:'user',text:'Continue from the evidence already collected. Return the three exact observations before changing code.',toolUses:[]});
 return {id:name,goal,gold,messages};
});
const options={preserveRecentMessages:6,keepThreshold:.5,truncateHeadChars:300,maxStateTokens:25000,maxRequestTokens:30000};
const bytes=x=>Buffer.byteLength(JSON.stringify(x));
const retained=(messages,gold)=>gold.map(f=>JSON.stringify(messages).includes(f));
const paired=messages=>{const uses=messages.flatMap(m=>m.toolUses.map(t=>t.tool_use_id));const results=messages.flatMap(m=>(m.toolResults??[]).map(t=>t.tool_use_id));return uses.length===new Set(uses).size&&uses.every(id=>results.includes(id))&&results.every(id=>uses.includes(id));};
// Same pinned messages, delete oldest whole pairs until no larger than Jev's output.
function recency(messages,target){const calls=collectToolCalls(messages,options.preserveRecentMessages);const decisions=calls.map(c=>({...c,action:'keep',keepCall:1,keepResult:1,reason:c.pinned?'pinned':'kept'}));let output=messages;for(const c of calls){if(bytes(output)<=target)break;if(c.pinned)continue;Object.assign(decisions.find(d=>d.id===c.id),{action:'drop_call',keepCall:0,keepResult:0,reason:'call_dropped'});output=applyDecisions(messages,decisions,calls,options.truncateHeadChars);}return output;}
save('plan.json',{kind:'synthetic component replay; not native Claude compaction',repeats:2,options,cases,source_sha256:createHash('sha256').update(readFileSync(new URL(import.meta.url))).digest('hex'),criteria:'Report gold retention, pair validity, serialized size and latency. All three facts retained is per-case success. No tuning. Recency receives same achieved size budget, no gold. Costs only if provider reports them.'});
const apiKey=readFileSync(process.env.TYPESAFE_API_KEY_FILE||`${process.env.HOME}/.config/jev-benchmark/typesafe-api-key`,'utf8').trim();
const client=new JevClient({apiKey,fetch:(url,options)=>fetch(url,{...options,signal:AbortSignal.timeout(20000)})});
const rows=[];
for(let repeat=1;repeat<=2;repeat++)for(const c of cases){
 const calls=[],start=performance.now();
 try{
  const result=await compact(c.messages,{ask:async(state,questions)=>{const t=performance.now();const answer=await client.ask(state,questions);calls.push({seconds:(performance.now()-t)/1000,model:answer.model,usage:answer.usage??null,questions:Object.keys(questions).length,state_bytes:bytes(state)});return answer;}},{...options,goal:c.goal});
  const baseline=recency(c.messages,bytes(result.messages));
  const row={id:c.id,repeat,seconds:(performance.now()-start)/1000,before_bytes:bytes(c.messages),after_bytes:bytes(result.messages),recency_bytes:bytes(baseline),retained:retained(result.messages,c.gold),recency_retained:retained(baseline,c.gold),pairs_valid:paired(result.messages),recency_pairs_valid:paired(baseline),stats:result.stats,calls,decisions:result.decisions,messages:result.messages,recency_messages:baseline};
  rows.push(row);save(`${c.id}-${repeat}.json`,row);console.log(JSON.stringify({id:c.id,repeat,retained:row.retained,recency:row.recency_retained,reduction:1-row.after_bytes/row.before_bytes,seconds:row.seconds}));
 }catch(e){const row={id:c.id,repeat,error:e.name,seconds:(performance.now()-start)/1000,calls};rows.push(row);save(`${c.id}-${repeat}.json`,row);console.log(JSON.stringify(row));}
}
save('results.json',rows);
