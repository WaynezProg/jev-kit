import {readFileSync,writeFileSync} from 'node:fs';
import {run} from '../../src/core.js';
const result=await run('evidence',JSON.parse(readFileSync(process.argv[2],'utf8')));
writeFileSync(process.argv[3],JSON.stringify(result),{flag:'wx',mode:0o600});
