import {z} from 'zod';import {readFileSync} from 'node:fs';import {schemas,descriptions} from '../../src/schema.js';import {traced} from './trace.mjs';
export default function(pi){
 for(const [mode,schema] of Object.entries(schemas))pi.registerTool({name:`jev_${mode}`,label:`Jev ${mode}`,description:descriptions[mode],parameters:z.toJSONSchema(schema),async execute(_id,args){const result=await traced(mode,args);return {content:[{type:'text',text:JSON.stringify(result)}],details:result};}});
 if(process.env.JEV_BENCH_INPUT){
  const mode=process.env.JEV_BENCH_MODE;if(!Object.hasOwn(schemas,mode))throw Error('Invalid benchmark file mode');
  pi.registerTool({name:`jev_${mode}_file`,label:'Jev file experiment',description:'Judge the exact input already provided by the benchmark runner without argument copying.',parameters:z.toJSONSchema(z.object({}).strict()),async execute(){const result=await traced(mode,JSON.parse(readFileSync(process.env.JEV_BENCH_INPUT,'utf8')));return {content:[{type:'text',text:JSON.stringify(result)}],details:result};}});
 }
}
