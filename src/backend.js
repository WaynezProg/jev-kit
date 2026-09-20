import {readFileSync} from 'node:fs';
import {homedir} from 'node:os';
import {BackendError,TypeSafeBackend} from 'jev-use';

const probability=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1;
export function validateAnswer(q,a){
 if(!a||typeof a.answer!=='string'||!Object.hasOwn(q.options,a.answer)||!probability(a.confidence))throw Error('invalid_choice_or_confidence');
 const d=a.distribution,keys=Object.keys(q.options);
 if(!d||typeof d!=='object'||Object.keys(d).length!==keys.length||keys.some(k=>!Object.hasOwn(d,k)||!probability(d[k])))throw Error('invalid_probabilities');
 if(Math.abs(Object.values(d).reduce((s,v)=>s+v,0)-1)>.02)throw Error('invalid_probability_sum');
 if(d[a.answer]+1e-6<Math.max(...Object.values(d)))throw Error('inconsistent_choice');
}
// Validation happens before jev-use turns raw answers into actionable verdicts.
export class StrictBackend{
 constructor(inner){this.inner=inner;this.name='typesafe';}
 async judge(request){
  try{
   const result=await this.inner.judge(request);
   if(!Array.isArray(result.answers)||result.answers.length!==request.questions.length)throw Error('answer_count');
   if(typeof result.model!=='string'||!result.model.trim()||result.model==='jev-latest')throw Error('missing_resolved_model');
   result.answers.forEach((a,i)=>validateAnswer(request.questions[i],a));
   return {...result,usage:Object.fromEntries(Object.entries(result.usage??{}).filter(([k,v])=>['inputTokens','outputTokens'].includes(k)&&Number.isSafeInteger(v)&&v>=0))};
  }catch{throw new BackendError('typesafe','provider_or_validation_error');}
 }
}
export function createBackend(){
 let key='';
 try{key=(process.env.TYPESAFE_API_KEY||readFileSync(process.env.TYPESAFE_API_KEY_FILE||`${homedir()}/.config/jev-benchmark/typesafe-api-key`,'utf8')).trim();}catch{}
 if(!key||/\s/.test(key))return {name:'unconfigured',async judge(){throw new BackendError('unconfigured','missing_or_invalid_api_key');}};
 const inner=new TypeSafeBackend({apiKey:key,timeoutMs:15000,maxRetries:0,defaultModel:'jev-latest'});
 return new StrictBackend({async judge(request){
  if(JSON.stringify(request).includes(key))throw Error('credential_in_payload');
  return inner.judge(request);
 }});
}
