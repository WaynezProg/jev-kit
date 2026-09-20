import {z} from 'zod';
import {schemas,descriptions} from './schema.js';
import {run} from './core.js';
// Native Pi tools: identical validation and semantics to MCP, no MCP adapter needed.
export default function(pi){
 for(const [mode,schema] of Object.entries(schemas))pi.registerTool({
  name:`jev_${mode}`,label:`Jev ${mode}`,description:descriptions[mode],
  parameters:z.toJSONSchema(schema),
  async execute(_id,params,signal){
   if(signal?.aborted)throw new Error('Cancelled');
   const result=await run(mode,params);
   return {content:[{type:'text',text:JSON.stringify(result)}],details:result};
  },
 });
}
