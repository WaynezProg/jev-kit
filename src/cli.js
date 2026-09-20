#!/usr/bin/env node
import {readFileSync,writeFileSync,statSync,existsSync} from 'node:fs';
import {run} from './core.js';
import {parseInput} from './schema.js';
import {serve} from './server.js';
async function stdin(){let parts=[],size=0;for await(const chunk of process.stdin){size+=chunk.length;if(size>1_000_000)throw Error('Input exceeds 1 MB');parts.push(chunk);}return Buffer.concat(parts).toString('utf8');}
try{
 const args=process.argv.slice(2),mode=args.shift();
 if(mode==='serve'){if(args.length)throw Error('serve accepts no arguments');await serve();}
 else if(!mode||['--help','help'].includes(mode))console.log('jev-kit serve\njev-kit evidence|classify|extract|decide --input FILE|- [--output NEW_FILE] [--validate-only]\nUses TYPESAFE_API_KEY or TYPESAFE_API_KEY_FILE; otherwise the existing ~/.config/jev-benchmark/typesafe-api-key.\nExit 0: processing complete, not approval. Exit 2: invalid input/service failure. Exit 3: review required.');
 else{
  let input='-',output,validate=false;
  for(let i=0;i<args.length;i++){if(args[i]==='--input'&&args[i+1])input=args[++i];else if(args[i]==='--output'&&args[i+1])output=args[++i];else if(args[i]==='--validate-only')validate=true;else throw Error('Unknown or incomplete argument');}
  if(output&&existsSync(output)){const e=Error('Output exists');e.code='EEXIST';throw e;}
  if(input!=='-'&&statSync(input).size>1_000_000)throw Error('Input exceeds 1 MB');
  const raw=input==='-'?await stdin():readFileSync(input,'utf8');if(Buffer.byteLength(raw)>1_000_000)throw Error('Input exceeds 1 MB');
  const data=JSON.parse(raw);parseInput(mode,data);
  const result=validate?{status:'valid',network_calls:0}:await run(mode,data);
  const encoded=JSON.stringify(result,null,2)+'\n';
  if(output)writeFileSync(output,encoded,{flag:'wx',mode:0o600});else process.stdout.write(encoded);
  process.exitCode=result.status==='partial'?2:result.results?.some(r=>r.requires_review)?3:0;
 }
}catch(error){
 // No input text, provider bodies or credential values in error output.
 process.stderr.write(JSON.stringify({status:'error',error:error?.code==='EEXIST'?'output_exists':error?.name==='ZodError'?'invalid_input':'input_or_runtime_error'})+'\n');process.exitCode=2;
}
