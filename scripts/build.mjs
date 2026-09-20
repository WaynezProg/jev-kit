import {build} from 'esbuild';
import {chmodSync} from 'node:fs';
const out=new URL('../dist/cli.js',import.meta.url).pathname;
await build({entryPoints:[new URL('../src/cli.js',import.meta.url).pathname],outfile:out,bundle:true,platform:'node',target:'node22',format:'esm',banner:{js:"import {createRequire as __createRequire} from 'node:module'; const require=__createRequire(import.meta.url);"},legalComments:'linked'});
await build({entryPoints:[new URL('../src/pi-extension.js',import.meta.url).pathname],outfile:new URL('../dist/pi-extension.js',import.meta.url).pathname,bundle:true,platform:'node',target:'node22',format:'esm',banner:{js:"import {createRequire as __createRequire} from 'node:module'; const require=__createRequire(import.meta.url);"},legalComments:'linked'});
await build({entryPoints:[new URL('../src/opencode-plugin.js',import.meta.url).pathname],outfile:new URL('../dist/opencode-plugin.js',import.meta.url).pathname,bundle:true,platform:'node',target:'node22',format:'esm',banner:{js:"import {createRequire as __createRequire} from 'node:module'; const require=__createRequire(import.meta.url);"},legalComments:'linked'});
chmodSync(out,0o755);
console.log('Built self-contained CLI, Pi extension, and OpenCode plugin');
