import {z} from 'zod';
import {descriptions,schemas} from './schema.js';
import {run} from './core.js';

async function execute(mode,input,context){
 if(context?.abort?.aborted)throw new Error('Cancelled');
 return JSON.stringify(await run(mode,input));
}

// OpenCode 1.x loads object modules through `server()`.
function tools(){
 return Object.fromEntries(Object.entries(schemas).map(([mode,schema])=>[
  `jev_${mode}`,{
   description:descriptions[mode],
   args:schema.shape,
   execute:(input,context)=>execute(mode,input,context),
  },
 ]));
}

export default {
 id:'jev-kit',
 async setup(context){
  if(typeof context?.tool?.transform!=='function')throw new Error('Unsupported OpenCode V2 runtime: ctx.tool.transform is required to register Jev tools');
  await context.tool.transform(editor=>{
   if(typeof editor?.namespace!=='function'||typeof editor?.add!=='function')throw new Error('Unsupported OpenCode V2 runtime: tool editor namespace() and add() are required');
   editor.namespace({name:'jev',description:'Source-bound evidence and bounded batch judgments.'});
   for(const [mode,schema] of Object.entries(schemas))editor.add({
    name:mode,description:descriptions[mode],input:z.toJSONSchema(schema),options:{namespace:'jev',codemode:true},
    execute:async input=>({content:await execute(mode,input)}),
   });
  });
 },
 async server(){return {tool:tools()};},
};
