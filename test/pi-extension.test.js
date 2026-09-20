import {test} from 'node:test';import assert from 'node:assert/strict';
import extension from '../dist/pi-extension.js';
test('Pi native tools preserve core no-network quote checks',async()=>{
 const tools=[];extension({registerTool:t=>tools.push(t)});
 assert.deepEqual(tools.map(t=>t.name).sort(),['jev_classify','jev_decide','jev_evidence','jev_extract','jev_rerank']);
 for(const t of tools)assert.equal(t.parameters.type,'object');
 const r=await tools.find(t=>t.name==='jev_evidence').execute('test',{items:[{id:'a',claim:'done',source_text:'pending',source_ref:'log',quote:'done'}]});
 assert.equal(r.details.results[0].verdict,'quote_not_found');assert.equal(r.details.calls.length,0);
 const ranked=await tools.find(t=>t.name==='jev_rerank').execute('rank',{query:'sum',candidates:[{id:'one',text:'sum(xs)'}]});
 assert.deepEqual(ranked.details.selected_ids,['one']);assert.equal(ranked.details.calls.length,0);
});
