// Benchmark adapter: exact prepared records go directly to the shipped core.
import {readFileSync,writeFileSync} from 'node:fs';
import {run} from '../../src/core.js';
const input=JSON.parse(readFileSync(process.argv[2],'utf8'));
const result=await run('classify',input);
writeFileSync(process.argv[3],JSON.stringify(result),{flag:'wx',mode:0o600});
