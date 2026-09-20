// Post-hoc v2 diagnostic. Never updates the frozen campaign's receipts.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {homedir} from 'node:os';
import {TypeSafeBackend} from '../../vendor/jev-use/dist/backends/typesafe.js';
import {rerank} from './frozen-rank-v2.mjs';
const [inputPath,out]=process.argv.slice(2);
const file=readFileSync(inputPath),input=JSON.parse(file);mkdirSync(out,{recursive:true,mode:0o700});
const save=(path,v)=>writeFileSync(path,JSON.stringify(v,null,2)+'\n',{flag:'wx',mode:0o600});
save(`${out}/plan.json`,{kind:'posthoc_rounding_diagnostic',input_sha256:createHash('sha256').update(file).digest('hex'),rank_sha256:createHash('sha256').update(readFileSync(new URL('./frozen-rank-v2.mjs',import.meta.url))).digest('hex'),cases:input.cases.map(c=>c.id),change:'Expectation tolerance 0.03 -> 0.035000001: account for probability/score rounding and floating point. Same 64 cases, no selection based on outcome. Original campaign untouched. No new Claude calls.'});
const key=(process.env.TYPESAFE_API_KEY||readFileSync(process.env.TYPESAFE_API_KEY_FILE||`${homedir()}/.config/jev-benchmark/typesafe-api-key`,'utf8')).trim();
if(!key||/\s/.test(key)||file.includes(Buffer.from(key)))throw Error('invalid_credentials_or_payload');
const backend=new TypeSafeBackend({apiKey:key,timeoutMs:15000,maxRetries:0});
const runs=[];
for(const c of input.cases){
 const start=performance.now();
 const r=await rerank({query:c.query,candidates:c.candidates.map((d,i)=>({id:`c${i}`,text:d.text}))},backend);
 const ids=r.ranked.map(d=>c.candidates[d.original_index].id),gold=new Set(c.gold_ids);
 const result={id:c.id,status:r.status,model:r.model??null,usage:r.usage??null,api_ms:r.api_ms??null,wall_ms:performance.now()-start,top1:gold.has(ids[0]),recall5:ids.slice(0,5).some(id=>gold.has(id)),top5:ids.slice(0,5)};
 save(`${out}/${c.id}.json`,result);runs.push(result);
 console.log(JSON.stringify({id:c.id,status:r.status,top1:result.top1,recall5:result.recall5}));
}
save(`${out}/runs.json`,runs);
