// Adapted from jkudish/jev-mcp 67dd9fa5 (MIT). See jev-mcp-LICENSE.
import {Worker} from 'node:worker_threads';
export function marginOf(p){const a=Object.values(p).sort((x,y)=>y-x);return a.length<2?0:a[0]-a[1];}
export function classificationDecision(top,margin){return top>=.85&&margin>=.5?'candidate':'review';}
export const escapes={ask_user:'A consequential user preference is missing; ask instead of inventing it',investigate:'Technical or factual evidence is missing; investigate before deciding',none:'None of the supplied alternatives fits the requirements'};
const workerCode=`const {parentPort,workerData}=require('node:worker_threads');
const {document,pattern,flags}=workerData;
try{const re=new RegExp(pattern,flags+'g'),seen=new Set(),candidates=[];let truncated=false,tooLong=0;
for(const m of document.matchAll(re)){const v=m[0];if(!v.length||seen.has(v))continue;seen.add(v);if(v.length>2000){tooLong++;continue;}if(candidates.length>=20){truncated=true;break;}candidates.push(v);}
parentPort.postMessage({candidates,truncated,tooLong});}catch{parentPort.postMessage({candidates:[],error:'invalid_pattern'});}`;
export function runRegex(document,pattern,flags=''){
 return new Promise(resolve=>{
  const w=new Worker(workerCode,{eval:true,workerData:{document,pattern,flags},resourceLimits:{maxOldGenerationSizeMb:32}});
  let settled=false;const finish=value=>{if(settled)return;settled=true;clearTimeout(timer);void w.terminate();resolve(value);};
  const timer=setTimeout(()=>finish({candidates:[],error:'regex_timeout'}),1000);
  w.on('message',finish);w.on('error',()=>finish({candidates:[],error:'regex_error'}));w.on('exit',()=>finish({candidates:[],error:'regex_exit'}));
 });
}
