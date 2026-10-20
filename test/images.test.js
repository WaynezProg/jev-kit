import {test} from 'node:test';import assert from 'node:assert/strict';import {spawnSync} from 'node:child_process';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';import {deflateSync,crc32} from 'node:zlib';
import {run} from '../src/core.js';import {StrictBackend,createBackend} from '../src/backend.js';import {parseInput} from '../src/schema.js';
import {sniff,MAX_IMAGE_BYTES} from '../src/images.js';

const chunk=(type,data)=>{const len=Buffer.alloc(4),crc=Buffer.alloc(4),body=Buffer.concat([Buffer.from(type,'latin1'),data]);len.writeUInt32BE(data.length);crc.writeUInt32BE(crc32(body));return Buffer.concat([len,body,crc]);};
function png(w,h,[r,g,b]){
 const ihdr=Buffer.alloc(13);ihdr.writeUInt32BE(w);ihdr.writeUInt32BE(h,4);ihdr.set([8,2,0,0,0],8);
 const row=Buffer.concat([Buffer.from([0]),Buffer.alloc(w*3).map((_,i)=>[r,g,b][i%3])]);
 return Buffer.concat([Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]),chunk('IHDR',ihdr),chunk('IDAT',deflateSync(Buffer.concat(Array(h).fill(row)))),chunk('IEND',Buffer.alloc(0))]);
}
// Header-only baseline JPEG: enough for magic bytes and SOF0 dimensions.
const jpg=(w,h)=>Buffer.from([0xff,0xd8,0xff,0xe0,0,4,0,0,0xff,0xc0,0,11,8,h>>8,h&255,w>>8,w&255,1,1,0x11,0,0xff,0xd9]);
function fixtures(t){
 const dir=mkdtempSync(join(tmpdir(),'jev-img-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const put=(name,data)=>{const p=join(dir,name);writeFileSync(p,data);return p;};
 return {dir,put,red:put('red.png',png(300,300,[255,0,0])),blue:put('blue.dat',png(300,300,[0,0,255])),jpeg:put('photo.png',jpg(640,480))};
}
const answer=q=>({answer:Object.keys(q.options)[0],confidence:.99,distribution:Object.fromEntries(Object.keys(q.options).map((k,i)=>[k,i===0?1:0]))});
function mock(){const requests=[];const b=new StrictBackend({async judge(r){requests.push(r);return {model:'jev-test',answers:r.questions.map(answer)};}});b.requests=requests;return b;}
const classes=[{id:'red',description:'red image'},{id:'blue',description:'blue image'}];
const referenced=r=>Object.keys(r.assets).every(k=>r.state.includes(k));

test('schema accepts images with or without text; rejects relative paths, >4 images and missing content',t=>{
 const f=fixtures(t);
 assert.doesNotThrow(()=>parseInput('classify',{purpose:'p',items:[{id:'a',images:[{path:f.red}]},{id:'b',text:'See',images:[{path:f.jpeg}]},{id:'c',text:'plain'}],classes}));
 assert.doesNotThrow(()=>parseInput('evidence',{items:[{id:'a',claim:'It is red',images:[{path:f.red}],source_ref:'shot'}]}));
 assert.doesNotThrow(()=>parseInput('decide',{decision:'d',evidence:'e',priorities:'p',candidates:[{id:'a',description:'A',images:[{path:f.red}]},{id:'b',description:'B'}]}));
 assert.throws(()=>parseInput('classify',{purpose:'p',items:[{id:'a',text:' '}],classes}));
 assert.throws(()=>parseInput('classify',{purpose:'p',items:[{id:'a',images:[{path:'red.png'}]}],classes}));
 assert.throws(()=>parseInput('classify',{purpose:'p',items:[{id:'a',images:Array(5).fill({path:f.red})}],classes}));
 assert.throws(()=>parseInput('evidence',{items:[{id:'a',claim:'x',images:[{path:f.red}],quote:'q',source_ref:'s'}]}));
});

test('format comes from magic bytes; non-images, tiny, oversized and unreadable files are rejected',t=>{
 const f=fixtures(t),bad=(path,reason)=>assert.throws(()=>parseInput('classify',{purpose:'p',items:[{id:'a',images:[{path}]}],classes}),e=>e.name==='ImageError'&&e.reason===reason&&e.where==='items[0].images[0]');
 assert.equal(sniff(png(300,300,[0,0,0])).format,'png');assert.equal(sniff(jpg(640,480)).format,'jpg');assert.deepEqual(sniff(jpg(640,480)).size,[640,480]);
 bad(f.put('fake.png',Buffer.from('GIF89a'+'\0'.repeat(64))),'unsupported_format');
 bad(f.put('small.png',png(64,64,[1,2,3])),'dimensions_out_of_range');
 bad(f.put('wide.jpg',jpg(2000,400)),'dimensions_out_of_range');
 bad(f.put('huge.png',Buffer.concat([png(300,300,[0,0,0]),Buffer.alloc(MAX_IMAGE_BYTES)])),'too_large');
 bad(join(f.dir,'missing.png'),'unreadable');
});

test('image items send referenced assets; text-only requests keep their old shape and no base64 reaches the receipt',async t=>{
 const f=fixtures(t),b=mock();
 const r=await run('classify',{purpose:'colour',items:[{id:'r',text:'',images:[{path:f.red}]},{id:'b',images:[{path:f.blue}]}],classes},b);
 const req=b.requests[0];
 assert.equal(Object.keys(req.assets).length,2);assert(referenced(req));
 assert(Object.values(req.assets).every(a=>a.type==='image'&&a.format==='png'&&/^[A-Za-z0-9+/]+=*$/.test(a.data_base64)));
 assert.match(req.questions[0].question,/items\[0\]\.images/);
 const out=JSON.stringify(r);for(const a of Object.values(req.assets))assert(!out.includes(a.data_base64.slice(0,64)));
 assert.equal(r.results[0].image_count,1);assert.equal(r.results[0].text_sha256!==null,true);assert.equal(r.results[1].text_sha256,null);assert.equal(r.calls[0].image_count,2);
 const plain=mock(),p=await run('classify',{purpose:'colour',items:[{id:'x',text:'red'}],classes},plain);
 assert(!('assets' in plain.requests[0]));assert.deepEqual(JSON.parse(plain.requests[0].state),{purpose:'colour',items:[{text:'red'}]});
 assert(!('image_count' in p.calls[0])&&!('image_count' in p.results[0]));
});

test('batches keep images with their item, cap images per request and use fresh refs per request',async t=>{
 const f=fixtures(t),b=mock();
 const items=Array.from({length:5},(_,i)=>({id:`i${i}`,text:`item ${i}`,images:Array(4).fill({path:i%2?f.blue:f.red})}));
 const r=await run('classify',{purpose:'colour',items,classes},b);
 assert.equal(b.requests.length,2);assert.deepEqual(b.requests.map(q=>Object.keys(q.assets).length),[16,4]);
 assert(b.requests.every(referenced));
 const all=b.requests.flatMap(q=>Object.keys(q.assets));assert.equal(new Set(all).size,all.length);
 for(const q of b.requests)JSON.parse(q.state).items.forEach(it=>{assert.equal(it.images.length,4);assert(it.images.every(ref=>Object.hasOwn(q.assets,ref)));});
 assert.deepEqual(r.results.map(x=>x.id),items.map(x=>x.id));
 // decide shares one state across several question batches: each request gets its own refs.
 const d=mock();
 await run('decide',{decision:'d',evidence:'e',priorities:'p',candidates:['a','b','c'].map(id=>({id,description:id,images:[{path:f.red}]})),requirements:['r1','r2','r3']},d);
 assert(d.requests.length>1&&d.requests.every(referenced));
 const refs=d.requests.flatMap(q=>Object.keys(q.assets));assert.equal(new Set(refs).size,refs.length);
 // evidence image rows are inline, never source-shared.
 const e=mock();
 await run('evidence',{items:[{id:'a',claim:'red',source_text:'same',images:[{path:f.red}],source_ref:'s'},{id:'b',claim:'blue',source_text:'same',source_ref:'s'}]},e);
 const st=JSON.parse(e.requests[0].state);assert(!st.sources);assert.equal(st.items[0].source_images.length,1);assert(!('source_images' in st.items[1]));assert(referenced(e.requests[0]));
 assert.match(e.requests[0].questions[0].question,/source_images/);assert.doesNotMatch(e.requests[0].questions[1].question,/source_images/);
});

test('TypeSafe transport adds assets and the images header only when images are present',async t=>{
 const f=fixtures(t),before={key:process.env.TYPESAFE_API_KEY,fetch:globalThis.fetch},seen=[];
 process.env.TYPESAFE_API_KEY='test-image-key';
 t.after(()=>{globalThis.fetch=before.fetch;if(before.key===undefined)delete process.env.TYPESAFE_API_KEY;else process.env.TYPESAFE_API_KEY=before.key;});
 globalThis.fetch=async(url,o)=>{const body=JSON.parse(o.body);seen.push({headers:o.headers,body});
  return new Response(JSON.stringify({model:'jev-1.14.0',answers:Object.fromEntries(Object.keys(body.questions).map(k=>[k,{choice:'c0',confidence:.99,probabilities:{c0:1,c1:0}}]))}),{status:200,headers:{'content-type':'application/json'}});};
 const img=await run('classify',{purpose:'colour',items:[{id:'r',images:[{path:f.red}]}],classes},createBackend());
 const txt=await run('classify',{purpose:'colour',items:[{id:'t',text:'red'}],classes},createBackend());
 assert.equal(seen.length,2);
 assert.equal(seen[0].headers['TypeSafe-Danger-Zone-Images'],'true');assert.equal(seen[0].headers.Authorization,'Bearer test-image-key');
 const [ref]=Object.keys(seen[0].body.assets);assert(seen[0].body.state.includes(ref));assert.equal(seen[0].body.model,img.calls[0].requested_model);
 assert(!('TypeSafe-Danger-Zone-Images' in seen[1].headers));assert(!('assets' in seen[1].body));
 assert.equal(img.calls[0].model,'jev-1.14.0');assert.equal(txt.status,'ok');
 assert(!JSON.stringify(img).includes(seen[0].body.assets[ref].data_base64.slice(0,64)));
});

test('CLI --validate-only checks images offline',t=>{
 const f=fixtures(t),cli=new URL('../src/cli.js',import.meta.url).pathname,env={PATH:process.env.PATH,TYPESAFE_API_KEY_FILE:'/missing-jev-test-key'};
 const invoke=items=>spawnSync(process.execPath,[cli,'classify','--input','-','--validate-only'],{env,input:JSON.stringify({purpose:'p',items,classes}),encoding:'utf8'});
 const ok=invoke([{id:'a',images:[{path:f.red},{path:f.jpeg}]}]);assert.equal(ok.status,0);assert.deepEqual(JSON.parse(ok.stdout),{status:'valid',network_calls:0,image_count:2});
 const bad=invoke([{id:'a',images:[{path:f.put('x.png',Buffer.from('not an image at all'))}]}]);assert.equal(bad.status,2);
 assert.deepEqual(JSON.parse(bad.stderr),{status:'error',error:'invalid_image',reason:'unsupported_format',at:'items[0].images[0]'});
});
