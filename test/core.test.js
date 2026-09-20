import {test} from 'node:test';import assert from 'node:assert/strict';
import {run,sha} from '../src/core.js';import {StrictBackend} from '../src/backend.js';
import {parseInput} from '../src/schema.js';import {runRegex} from '../vendor/mcp-helpers.js';
const input={items:[{id:'a',claim:'All tests passed.',source_text:' Two tests failed. ',source_ref:'local:17',quote:' Two'}]};
function pick(q,answer=Object.keys(q.options)[0],confidence=.98){const keys=Object.keys(q.options);return {answer,confidence,distribution:Object.fromEntries(keys.map(k=>[k,k===answer?.toString()?.trim()?1:0]))};}
// Expose only StrictBackend in tests, matching production validation order.
function mock(fn){const requests=[];const b=new StrictBackend({async judge(r){requests.push(r);return {model:'jev-test',answers:r.questions.map((q,i)=>fn(q,r,i)),usage:{inputTokens:7,outputTokens:2}};}});b.requests=requests;return b;}
test('quote precheck is local and source whitespace/hash survive',async()=>{
 const b=mock(q=>pick(q,'contradicts'));const r=await run('evidence',input,b);
 assert.equal(r.results[0].source_sha256,sha(input.items[0].source_text));assert.equal(r.results[0].quote_found,true);assert.equal(r.results[0].verdict,'contradicts');
 assert.equal(JSON.parse(b.requests[0].state).items[0].source_text,input.items[0].source_text);
 const out=await run('evidence',{items:[{...input.items[0],quote:'absent'}]},b);assert.equal(out.calls.length,0);assert.equal(out.results[0].verdict,'quote_not_found');
});
test('batching retains IDs/source mapping and does not send references',async()=>{
 const b=mock(q=>pick(q,'insufficient'));const rows=Array.from({length:17},(_,i)=>({...input.items[0],id:String(i),source_ref:`private-${i}`}));
 const r=await run('evidence',{items:rows},b);assert.equal(b.requests.length,3);assert.deepEqual(r.results.map(x=>x.id),rows.map(x=>x.id));assert(!JSON.stringify(b.requests).includes('private-'));
});
for(const [name,edit] of Object.entries({unknown:a=>({...a,answer:'invented'}),negative:a=>({...a,distribution:{supports:2,contradicts:-1,insufficient:0}}),sum:a=>({...a,distribution:{supports:.4,contradicts:.4,insufficient:.4}}),inconsistent:a=>({...a,answer:'contradicts'}),confidence:a=>({...a,confidence:2}),missingConfidence:a=>({...a,confidence:undefined}),missingKey:a=>({...a,distribution:{supports:1}})})){
 test(`invalid ${name} always reviews`,async()=>{const r=await run('evidence',input,mock(q=>edit(pick(q,'supports'))));assert.equal(r.status,'partial');assert.equal(r.results[0].verdict,'review');assert.equal(r.results[0].requires_review,true);});
}
test('low confidence preserves raw guess but not settled verdict',async()=>{const r=await run('evidence',input,mock(q=>pick(q,'supports',.2)));assert.equal(r.results[0].relation,'supports');assert.equal(r.results[0].verdict,'review');});
test('provider error details never enter receipt',async()=>{const b=new StrictBackend({async judge(){throw Error('secret-value-from-provider');}});const r=await run('evidence',input,b);assert(!JSON.stringify(r).includes('secret-value'));assert.equal(r.status,'partial');});
test('missing answer count / model escalates',async()=>{for(const response of [{model:'jev-test',answers:[]},{answers:[{}]}]){const b=new StrictBackend({async judge(){return response;}});assert.equal((await run('evidence',input,b)).results[0].verdict,'review');}});
test('duplicate IDs and unknown keys rejected; no silent truncation',()=>{assert.throws(()=>parseInput('evidence',{items:[input.items[0],input.items[0]]}));assert.throws(()=>parseInput('evidence',{...input,extra:true}));assert.throws(()=>parseInput('evidence',{items:[{...input.items[0],source_text:'x'.repeat(80001)}]}));});
test('classification preserves hostile ID strings and explicit manual-review class',async()=>{
 const d={purpose:'triage',items:[{id:'__proto__',text:'uncertain'}],classes:[{id:'constructor',description:'Known'},{id:'manual_review',description:'Unknown'}]};
 const r=await run('classify',d,mock(q=>pick(q,'c1')));assert.equal(r.results[0].id,'__proto__');assert.equal(r.results[0].classification,'manual_review');assert.equal(r.results[0].requires_review,true);
});
test('classification needs both top probability and margin',async()=>{
 const d={purpose:'triage',items:[{id:'i',text:'maybe'}],classes:[{id:'a',description:'A'},{id:'b',description:'B'}]};
 const r=await run('classify',d,mock(q=>({answer:'c0',confidence:.98,distribution:{c0:.6,c1:.4}})));assert(r.results[0].requires_review);
});
test('extract returns original substring, absent matches avoid API',async()=>{
 const d={document:'old 1.2.0; release 2.1.0',source_ref:'notes',fields:[{id:'v',description:'Release version',pattern:'[0-9]+\\.[0-9]+\\.[0-9]+'}]};
 const b=mock(q=>pick(q,'c1')),r=await run('extract',d,b);assert.equal(r.results[0].value,'2.1.0');assert(d.document.includes(r.results[0].value));
 const absent=await run('extract',{...d,document:'no version'},b);assert.equal(absent.calls.length,0);assert.equal(absent.results[0].status,'not_found');
});
test('extract incomplete candidates never returns an accepted value',async()=>{
 const r=await run('extract',{document:Array.from({length:21},(_,i)=>`v${i}`).join(' '),source_ref:'notes',fields:[{id:'v',description:'version',pattern:'v[0-9]+'}]},mock(q=>pick(q,'c0')));
 assert.equal(r.results[0].value,null);assert.equal(r.results[0].requires_review,true);assert.equal(r.results[0].candidates_truncated,true);
});
test('invalid and catastrophic regex are bounded',async()=>{assert.equal((await runRegex('abc','[')).error,'invalid_pattern');assert.equal((await runRegex('a'.repeat(20000)+'!','(a+)+$')).error,'regex_timeout');});
test('decision cannot settle when its requirement is unknown',async()=>{
 const d={decision:'Choose',evidence:'Unknown throughput',priorities:'Needs >100/s',candidates:[{id:'local',description:'A'},{id:'cloud',description:'B'}],requirements:['100/s']};
 const r=await run('decide',d,mock(q=>pick(q,q.id==='select'?'c0':'unknown')));assert.equal(r.results[0].selected,'local');assert.equal(r.results[0].requires_review,true);assert.equal(r.results[0].review_reason,'unresolved_requirement');
});
test('escape is separate from user IDs and remains review',async()=>{
 const d={decision:'Choose',evidence:'No facts',priorities:'Investigate first',candidates:[{id:'investigate',description:'A'},{id:'none',description:'B'}]};
 const r=await run('decide',d,mock(q=>pick(q,'investigate')));assert.equal(r.results[0].selected,null);assert.equal(r.results[0].escape,'investigate');assert(r.results[0].requires_review);
});
