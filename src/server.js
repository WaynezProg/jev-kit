import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {StdioServerTransport} from '@modelcontextprotocol/sdk/server/stdio.js';
import {schemas,descriptions} from './schema.js';
import {run} from './core.js';
export function createServer(backend){
 const server=new McpServer({name:'jev-kit',version:'0.3.0'});
 for(const mode of Object.keys(schemas))server.registerTool(`jev_${mode}`,{
  description:descriptions[mode],inputSchema:schemas[mode],
  annotations:{readOnlyHint:true,destructiveHint:false,idempotentHint:false,openWorldHint:true},
 },async args=>({content:[{type:'text',text:JSON.stringify(await run(mode,args,backend))}]}));
 return server;
}
export async function serve(){await createServer().connect(new StdioServerTransport());}
