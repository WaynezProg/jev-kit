import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {StdioServerTransport} from '@modelcontextprotocol/sdk/server/stdio.js';
import {schemas,descriptions} from '../../src/schema.js';
import {traced} from './trace.mjs';
import {readFileSync} from 'node:fs';
import {z} from 'zod';
const server=new McpServer({name:'jev-kit-benchmark',version:'0.2.0'});
for(const [mode,schema] of Object.entries(schemas))server.registerTool(`jev_${mode}`,{description:descriptions[mode],inputSchema:schema,annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:true}},async args=>({content:[{type:'text',text:JSON.stringify(await traced(mode,args))}]}));
// Experimental file adapter: only a runner-configured input, never arbitrary model paths.
if(process.env.JEV_BENCH_INPUT){
 const mode=process.env.JEV_BENCH_MODE;
 if(!Object.hasOwn(schemas,mode))throw Error('Invalid benchmark file mode');
 server.registerTool(`jev_${mode}_file`,{description:'Judge the exact input already provided by the benchmark runner. No argument copying is needed.',inputSchema:z.object({}).strict(),annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:true}},async()=>({content:[{type:'text',text:JSON.stringify(await traced(mode,JSON.parse(readFileSync(process.env.JEV_BENCH_INPUT,'utf8'))))}]}));
}
await server.connect(new StdioServerTransport());
