import {test} from 'node:test';import assert from 'node:assert/strict';
import plugin from '../dist/opencode-plugin.js';
const names=['jev_classify','jev_decide','jev_evidence','jev_extract','jev_rerank'];

test('OpenCode V1 server registers the five native Jev tools',async()=>{
 const hooks=await plugin.server({});
 assert.deepEqual(Object.keys(hooks.tool).sort(),names);
 for(const tool of Object.values(hooks.tool))assert.equal(typeof tool.execute,'function');
});

test('OpenCode V2 setup registers the five native tools through ctx.tool.transform',async()=>{
 const namespaces=[],added=[];
 const context={tool:{async transform(callback){callback({namespace:value=>namespaces.push(value),add:value=>added.push(value)});return {dispose:async()=>{}};}}};
 assert.equal(plugin.id,'jev-kit');
 assert.equal(typeof plugin.setup,'function');
 await plugin.setup(context);
 assert.deepEqual(namespaces,[{name:'jev',description:'Source-bound evidence and bounded batch judgments.'}]);
 assert.deepEqual(added.map(tool=>`jev_${tool.name}`).sort(),names);
 for(const tool of added){assert.equal(tool.input.type,'object');assert.deepEqual(tool.options,{namespace:'jev',codemode:true});}
 const evidence=added.find(tool=>tool.name==='evidence');
 const result=JSON.parse((await evidence.execute({items:[{id:'a',claim:'done',source_text:'pending',source_ref:'log',quote:'done'}]},{})).content);
 assert.equal(result.results[0].verdict,'quote_not_found');assert.equal(result.calls.length,0);
 await assert.rejects(evidence.execute({items:[]},{}));
});

test('OpenCode native evidence tool returns local quote_not_found without a key',async()=>{
 const {tool}=await plugin.server({});
 const result=JSON.parse(await tool.jev_evidence.execute({items:[{id:'a',claim:'done',source_text:'pending',source_ref:'log',quote:'done'}]},{}));
 assert.equal(result.results[0].verdict,'quote_not_found');assert.equal(result.calls.length,0);
});

test('OpenCode native tools reject malformed input',async()=>{
 const {tool}=await plugin.server({});
 await assert.rejects(tool.jev_evidence.execute({items:[]},{}));
});

test('OpenCode V2 rejects a runtime without the native tool registrar',async()=>{
 await assert.rejects(plugin.setup({options:{}}),/ctx\.tool\.transform/);
});
