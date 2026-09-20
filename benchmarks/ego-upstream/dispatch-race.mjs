import {createServer} from 'node:http';
import {writeFileSync} from 'node:fs';
import {runBrowser,acquirePageLease} from '../../integrations/ego-browser/adapter.mjs';
export async function runDispatchRace(page,{upstream,output}){
 const server=createServer((req,res)=>res.end('<!doctype html><h1>Ready</h1><button onclick="document.querySelector(\'h1\').textContent=\'Complete\';window.clicks=(window.clicks||0)+1">Continue</button>'));
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const url=`http://127.0.0.1:${server.address().port}`;
 const release=acquirePageLease(page);let replaced=false,decisions=0;
 const injected=new Proxy(page,{get(target,key){if(key==='click')return async(...args)=>{
  if(!replaced){replaced=true;await page.evaluate(()=>{const e=document.querySelector('button'),replacement=e.cloneNode(true);replacement.removeAttribute('data-jev-kit-target');e.replaceWith(replacement);});}
  return page.click(...args);
 };const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value;}});
 try{
  const result=await runBrowser(injected,{upstream,url,goal:'Continue to Complete',maxSteps:4,policy:{choose:async state=>{decisions++;return {choice:state.text.includes('Complete')?'DONE':state.actions.find(a=>a.label==='Continue').id};}},verify:async page=>await page.evaluate(()=>window.clicks===1&&document.querySelector('h1').textContent==='Complete')});
  const evidence={case:'replacement_between_guard_and_dispatch',pass:result.verified&&decisions===3&&result.executed_actions===1&&result.steps[0].discarded==='target_disappeared_before_dispatch',decisions,result};
  writeFileSync(output,JSON.stringify(evidence,null,2)+'\n',{flag:'wx',mode:0o600});return {pass:evidence.pass,status:result.status,decisions,executed_actions:result.executed_actions};
 }finally{server.close();server.closeAllConnections();release();}
}
