// Generate host-neutral stdio configuration for this installation location.
import {writeFileSync} from 'node:fs';
const root=new URL('../',import.meta.url);
writeFileSync(new URL('.mcp.json',root),JSON.stringify({mcpServers:{'jev-kit':{command:process.execPath,args:[new URL('dist/cli.js',root).pathname,'serve']}}},null,2)+'\n');
console.log('Updated .mcp.json for this installation directory. No host configuration changed.');
