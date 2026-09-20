import {z} from 'zod';
import {validateRerankInput} from './rerank.js';
const text=(n)=>z.string().min(1).max(n).refine(v=>v.trim().length>0,'Text must not be blank');
const id=text(128);
const unique=(rows)=>new Set(rows.map(r=>r.id)).size===rows.length;
const list=(schema,max)=>z.array(schema).min(1).max(max).refine(unique,'IDs must be unique');
export const schemas={
 rerank:z.object({query:text(8000),candidates:list(z.object({id,text:text(24000),source_ref:text(2048).optional()}).strict(),30),top_k:z.number().int().min(1).max(30).optional()}).strict().refine(v=>v.top_k===undefined||v.top_k<=v.candidates.length,'top_k exceeds candidate count'),
 evidence:z.object({items:list(z.object({id,claim:text(8000),source_text:text(80000),source_ref:text(2048),quote:z.string().min(1).max(80000).nullable().optional()}).strict(),256)}).strict(),
 classify:z.object({purpose:text(2000),items:list(z.object({id,text:text(8000)}).strict(),64),classes:list(z.object({id,description:text(2000),requires_review:z.boolean().optional()}).strict(),32).refine(a=>a.length>=2,'At least two classes required')}).strict(),
 extract:z.object({document:text(50000),source_ref:text(2048),fields:list(z.object({id,description:text(1500),pattern:text(500),flags:z.string().regex(/^[imsu]*$/).optional()}).strict(),8)}).strict(),
 decide:z.object({decision:text(1500),evidence:text(12000),priorities:text(2000),candidates:list(z.object({id,description:text(2000)}).strict(),6).refine(a=>a.length>=2,'At least two candidates required'),requirements:z.array(text(500)).max(3).default([])}).strict(),
};
export function parseInput(mode,value){
 if(!Object.hasOwn(schemas,mode))throw new Error('Unknown tool');
 if(Buffer.byteLength(JSON.stringify(value))>1_000_000)throw new Error('Input exceeds 1 MB; split without truncating sources');
 const data=schemas[mode].parse(value);
 if(mode==='rerank')validateRerankInput(data);
 return data;
}
export const descriptions={
 rerank:'Optionally rank 1–30 existing candidate texts for a query when lexical ordering is insufficient. Returns every candidate ID, hash and source reference; top_k only selects a prefix, never deletes candidates. Does not search, execute, certify relevance or prune context. Source references stay local. On failure preserves original order with review flags.',
 evidence:'Check batches of existing claim/source pairs. Exact quotes are checked locally; Jev judges only each assigned source. Returns source hashes and review flags. No browsing, truth certification, or task approval.',
 classify:'Classify existing texts against a shared catalog in batches. Use for repeated semantic classification; explicit error codes belong in ordinary code. Uncertain results remain review.',
 extract:'Extract exact source substrings: bounded regex workers produce candidates, then Jev selects by field meaning. Oversized or incomplete candidate sets stay review; never invents a value.',
 decide:'Compare 2–6 supplied alternatives using existing evidence and explicit priorities. Checks up to 3 requirements; missing evidence or conflicting checks return review. Advisory only; does not execute actions or grant permission.',
};
