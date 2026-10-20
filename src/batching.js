import {DEFAULT_MAX_STATE_TOKENS} from '../vendor/jev-use/dist/protocol.js';
import {MAX_REQUEST_IMAGE_BYTES,MAX_REQUEST_IMAGES} from './images.js';

// Keep the tested question count; overlap independent requests, not questions.
export const MAX_BATCH_ITEMS=8;
export const MAX_CONCURRENCY=4;
export const MAX_STATE_CHARS=DEFAULT_MAX_STATE_TOKENS*4;

export async function mapConcurrent(items,worker,limit=MAX_CONCURRENCY){
 const results=new Array(items.length);let next=0;
 await Promise.all(Array.from({length:Math.min(limit,items.length)},async()=>{
  while(next<items.length){const index=next++;results[index]=await worker(items[index],index);}
 }));
 return results;
}

// An oversized singleton remains whole: judge will hand it back for review.
// images(row) lists the row's loaded images; they always travel with their row.
export function packRows(rows,makeState,images=()=>[]){
 const batches=[];let current=[],bytes=0,count=0;
 for(const row of rows){
  const candidate=[...current,row],own=images(row)??[],b=own.reduce((s,x)=>s+x.bytes,0);
  if(current.length&&(candidate.length>MAX_BATCH_ITEMS||bytes+b>MAX_REQUEST_IMAGE_BYTES||count+own.length>MAX_REQUEST_IMAGES||JSON.stringify(makeState(candidate)).length>MAX_STATE_CHARS)){
   batches.push(current);current=[row];bytes=b;count=own.length;
  }else{current=candidate;bytes+=b;count+=own.length;}
 }
 if(current.length)batches.push(current);
 return batches;
}

// Exact strings only. IDs, references and source bodies in receipts stay local.
// imageRefs(row) returns asset references; image rows are never source-shared.
export function evidenceState(rows,imageRefs){
 if(imageRefs&&rows.some(r=>r.images?.length))return {items:rows.map(r=>{const refs=imageRefs(r);return {claim:r.claim,source_text:r.source_text??null,...(refs.length?{source_images:refs}:{}),quote:r.quote??null};})};
 const inline={items:rows.map(r=>({claim:r.claim,source_text:r.source_text,quote:r.quote??null}))};
 const sources=[],byText=new Map();
 const items=rows.map(r=>{
  if(!byText.has(r.source_text)){byText.set(r.source_text,sources.length);sources.push(r.source_text);}
  return {claim:r.claim,source_index:byText.get(r.source_text),quote:r.quote??null};
 });
 const shared={sources,items};
 return sources.length<rows.length&&JSON.stringify(shared).length<JSON.stringify(inline).length?shared:inline;
}
