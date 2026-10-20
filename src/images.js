import {readFileSync,statSync} from 'node:fs';
import {createHash,randomUUID} from 'node:crypto';

// TypeSafe images are experimental; limits stay below the documented API caps.
export const MAX_IMAGES_PER_ITEM=4;
export const MAX_IMAGE_BYTES=8*1024*1024;
export const MAX_REQUEST_IMAGE_BYTES=20*1024*1024;
export const MAX_REQUEST_IMAGES=16;
export const IMAGE_HEADER={'TypeSafe-Danger-Zone-Images':'true'};
const MIN_SIDE=280,MAX_SIDE=1568;

export class ImageError extends Error{
 constructor(reason,where){super(`invalid_image:${reason}${where?` at ${where}`:''}`);this.name='ImageError';this.reason=reason;this.where=where;}
}

function pngSize(b){
 if(b.length<24||b.toString('latin1',12,16)!=='IHDR')return null;
 for(let o=8;o+8<=b.length;){const len=b.readUInt32BE(o),type=b.toString('latin1',o+4,o+8);if(type==='acTL')return 'animated';if(type==='IDAT'||type==='IEND')break;o+=12+len;}
 return [b.readUInt32BE(16),b.readUInt32BE(20)];
}
function jpgSize(b){
 for(let o=2;o+9<b.length;){
  if(b[o]!==0xff){o++;continue;}
  const m=b[o+1];if(m===0xff){o++;continue;}
  if(m===0xd8||m===0x01||(m>=0xd0&&m<=0xd7)){o+=2;continue;}
  if(m===0xd9||m===0xda)return null;
  if(m>=0xc0&&m<=0xcf&&![0xc4,0xc8,0xcc].includes(m))return [b.readUInt16BE(o+7),b.readUInt16BE(o+5)];
  o+=2+b.readUInt16BE(o+2);
 }
 return null;
}
// Format comes from magic bytes; the file extension is ignored.
export function sniff(b){
 if(b.length>=8&&b.subarray(0,8).equals(Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a])))return {format:'png',size:pngSize(b)};
 if(b.length>=3&&b[0]===0xff&&b[1]===0xd8&&b[2]===0xff)return {format:'jpg',size:jpgSize(b)};
 return null;
}

export function loadImage(path,where){
 let st;try{st=statSync(path);}catch{throw new ImageError('unreadable',where);}
 if(!st.isFile())throw new ImageError('not_a_file',where);
 if(st.size>MAX_IMAGE_BYTES)throw new ImageError('too_large',where);
 let data;try{data=readFileSync(path);}catch{throw new ImageError('unreadable',where);}
 if(data.length>MAX_IMAGE_BYTES)throw new ImageError('too_large',where);
 const kind=sniff(data);
 if(!kind)throw new ImageError('unsupported_format',where);
 if(kind.size==='animated')throw new ImageError('animated_png',where);
 if(!kind.size)throw new ImageError('unreadable_dimensions',where);
 const [w,h]=kind.size;
 if(w<MIN_SIDE||h<MIN_SIDE||w>MAX_SIDE||h>MAX_SIDE)throw new ImageError('dimensions_out_of_range',where);
 return {path,format:kind.format,bytes:data.length,width:w,height:h,sha256:createHash('sha256').update(data).digest('hex'),data_base64:data.toString('base64')};
}

// Where each mode keeps per-item images; extract and rerank have none.
const holders={evidence:d=>d.items.map((r,i)=>[r,`items[${i}]`]),classify:d=>d.items.map((r,i)=>[r,`items[${i}]`]),decide:d=>d.candidates.map((r,i)=>[r,`candidates[${i}]`])};

// Reads and checks every image; returns Map(row -> loaded images). No network.
export function loadImages(mode,data){
 const out=new Map();let total=0,count=0;
 for(const [row,where] of holders[mode]?.(data)??[]){
  if(!row.images?.length)continue;
  const loaded=row.images.map((img,j)=>loadImage(img.path,`${where}.images[${j}]`));
  const bytes=loaded.reduce((s,x)=>s+x.bytes,0);
  if(bytes>MAX_REQUEST_IMAGE_BYTES)throw new ImageError('item_images_too_large',where);
  out.set(row,loaded);total+=bytes;count+=loaded.length;
 }
 // decide sends every candidate in one shared state.
 if(mode==='decide'&&(total>MAX_REQUEST_IMAGE_BYTES||count>MAX_REQUEST_IMAGES))throw new ImageError('request_images_too_large','candidates');
 return out;
}

// One registry per request: fresh UUID per image use; only referenced images become assets.
export function imageRegistry(){
 const used=new Map();
 return {ref(img){const r=randomUUID();used.set(r,img);return r;},
  assets(encoded){const a={};for(const [r,img] of used)if(encoded.includes(r))a[r]={type:'image',format:img.format,data_base64:img.data_base64};return a;},
  get size(){return used.size;}};
}
export const PLACEHOLDER_REF='00000000-0000-4000-8000-000000000000';
export const imageMeta=imgs=>imgs?.length?{image_count:imgs.length,image_sha256:imgs.map(i=>i.sha256)}:{};
