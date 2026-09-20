import {readFileSync,existsSync,statSync,mkdtempSync,writeFileSync,rmSync,accessSync,constants} from 'node:fs';
import {spawn} from 'node:child_process';
import {resolve,join,dirname} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {checkUpstream} from './adapter.mjs';
export function validateJob(job){
 const fields=['upstream','python','url','goal','origins','max_steps','max_seconds','space_id','page','expect_url','expect_text','output','claude_path'];
 if(!job||typeof job!=='object'||Array.isArray(job)||Object.keys(job).some(k=>!fields.includes(k)))throw Error('invalid_job');
 for(const key of ['upstream','python','url','goal'])if(typeof job[key]!=='string'||!job[key].trim())throw Error('invalid_job');
 if(job.goal.length>8000||!['http:','https:'].includes(new URL(job.url).protocol))throw Error('invalid_job');
 if(job.max_steps!==undefined&&(!Number.isInteger(job.max_steps)||job.max_steps<1||job.max_steps>60))throw Error('invalid_step_budget');
 if(job.max_seconds!==undefined&&(!Number.isFinite(job.max_seconds)||job.max_seconds<1||job.max_seconds>600))throw Error('invalid_time_budget');
 if(job.space_id!==undefined&&(!Number.isInteger(job.space_id)||job.space_id<1))throw Error('invalid_space');
 if(job.page!==undefined&&(typeof job.page!=='string'||!/^p[1-9][0-9]*$/.test(job.page)||(!job.space_id&&job.page!=='p1')))throw Error('invalid_page');
 for(const k of ['expect_url','expect_text','output','claude_path'])if(job[k]!==undefined&&(typeof job[k]!=='string'||!job[k]))throw Error('invalid_job');
 if(!job.expect_url&&!job.expect_text)throw Error('independent_completion_check_required');
 if(job.origins!==undefined&&(!Array.isArray(job.origins)||!job.origins.length||job.origins.some(s=>typeof s!=='string'||!['http:','https:'].includes(new URL(s).protocol)||new URL(s).origin!==s)))throw Error('invalid_origins');
 if(job.origins&&!job.origins.includes(new URL(job.url).origin))throw Error('initial_origin_out_of_scope');
 if(job.expect_url&&(!['http:','https:'].includes(new URL(job.expect_url).protocol)||!(job.origins??[new URL(job.url).origin]).includes(new URL(job.expect_url).origin)))throw Error('expectation_out_of_scope');
 return job;
}
async function main(){
 const args=process.argv.slice(2);
 if(args.length===0||args[0]==='--help'){console.log('Experimental: jev browser --input JOB.json [--validate-only]\nRequires ego-browser, a pinned jev-ultrafast checkout and its Python environment. See integrations/ego-browser/README.md. Does not install host hooks.');return;}
 if(args[0]!=='--input'||!args[1]||args.slice(2).some(a=>a!=='--validate-only'))throw Error('invalid_arguments');
 if(statSync(args[1]).size>64000)throw Error('job_too_large');
 const job=validateJob(JSON.parse(readFileSync(args[1],'utf8')));job.upstream=resolve(job.upstream);job.python=resolve(job.python);
 checkUpstream(job.upstream);
 if(!existsSync(job.python))throw Error('python_missing');
 if(job.claude_path){job.claude_path=resolve(job.claude_path);if(!existsSync(job.claude_path))throw Error('claude_missing');}
 if(job.output){job.output=resolve(job.output);if(existsSync(job.output))throw Error('output_exists');accessSync(dirname(job.output),constants.W_OK);}
 if(args.includes('--validate-only')){console.log(JSON.stringify({status:'valid',network_calls:0}));return;}
 const moduleUrl=new URL('./adapter.mjs',import.meta.url).href;
 const textUrl=new URL('./native-text.mjs',import.meta.url).href;
 const control=mkdtempSync(join(tmpdir(),'jev-browser-job-'));
 const stopFile=join(control,'stop'),receiptFile=join(control,'result.json');
 const cancel=()=>{writeFileSync(stopFile,'stop',{mode:0o600});console.error(JSON.stringify({status:'cancellation_requested',stop_file:stopFile,note:'Embedded code stops at the next checkpoint.'}));};
 process.on('SIGINT',cancel);process.on('SIGTERM',cancel);
 const script=`
 const job=${JSON.stringify(job)};
 const {writeFileSync,existsSync}=await import('node:fs');
 const {runBrowser,UpstreamPolicy,acquirePageLease}=await import(${JSON.stringify(moduleUrl)});
 const {createNativeTextHelper}=await import(${JSON.stringify(textUrl)});
 const task=await taskSpace(job.space_id??'Jev Kit browser');
 const page=task.page(job.page??'p1');
 console.log(JSON.stringify({space_id:task.spaceId,page:page.label,stop_file:${JSON.stringify(stopFile)}}));
 let result,policy,nativeText,release;
 const cleanupErrors=[];
 try{
  release=acquirePageLease(page);
  policy=new UpstreamPolicy(job.upstream,job.python);
  nativeText=job.claude_path?createNativeTextHelper(job.claude_path):null;
  result=await runBrowser(page,{...job,maxSteps:job.max_steps??16,maxSeconds:job.max_seconds??180,shouldStop:()=>existsSync(${JSON.stringify(stopFile)}),policy,textHelper:nativeText?.text,verify:async page=>(!job.expect_url||await page.url()===job.expect_url)&&(!job.expect_text||await page.evaluate(text=>document.body.innerText.includes(text),job.expect_text))});
 }catch(e){result={status:'error',error:e.message,verified:false,steps:[]};}
 finally{
  for(const cleanup of [()=>policy?.close(),()=>nativeText?.close(),()=>release?.()]){try{await cleanup();}catch(e){cleanupErrors.push(e.message);}}
 }
 result.space_id=task.spaceId;
 result.page=page.label;
 if(cleanupErrors.length){result.outcome_verified=result.verified;result.verified=false;result.status='cleanup_failed';result.cleanup_errors=cleanupErrors;}
 if(result.verified&&!job.space_id){try{result.finish=await task.finish({keep:[]});}catch(e){result.outcome_verified=true;result.verified=false;result.status='finish_failed';result.error=e.message;}}
 writeFileSync(${JSON.stringify(receiptFile)},JSON.stringify(result),{flag:'wx',mode:0o600});
 if(job.output)writeFileSync(job.output,JSON.stringify(result,null,2)+'\\n',{flag:'wx',mode:0o600});
 console.log(JSON.stringify(result));
 if(!result.verified)throw Error('browser_task_unverified');
 `;
 let childStarted=false;
 try{
  const child=spawn('ego-browser',['nodejs'],{stdio:['pipe','inherit','inherit']});child.stdin.end(script);
  child.once('spawn',()=>{childStarted=true;});
  child.stdin.on('error',()=>{});
  await new Promise((res,rej)=>{child.once('error',()=>rej(Error('ego_browser_unavailable')));child.once('exit',code=>code===0?res():rej(Error('browser_task_failed')));});
 }finally{
  process.off('SIGINT',cancel);process.off('SIGTERM',cancel);
  if(!childStarted||existsSync(receiptFile))rmSync(control,{recursive:true,force:true});
  else{writeFileSync(stopFile,'stop',{mode:0o600});console.error(JSON.stringify({status:'completion_unconfirmed',stop_file:stopFile}));}
 }
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(e=>{console.error(JSON.stringify({status:'error',error:e.message}));process.exitCode=2;});
