import {appendFileSync} from 'node:fs';
import {run} from '../../src/core.js';
export async function traced(mode,args){
 const start=performance.now();
 const result=await run(mode,args);
 if(process.env.JEV_BENCH_TRACE)appendFileSync(process.env.JEV_BENCH_TRACE,JSON.stringify({mode,input:args,result,wall_ms:performance.now()-start})+'\n',{mode:0o600});
 return result;
}
