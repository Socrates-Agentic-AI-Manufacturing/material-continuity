const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const sandbox = {};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../apps/web/workflow.js'), 'utf8'), sandbox);
const workflow = sandbox.AgentWorkflow;
function fixture() {
  const current = {case_version:2,case_hash:'current-hash',trigger:{trigger_type:'DELIVERY_DELAY'},exposure:{shortage_date:'2026-10-04'},
    recovery_options:{approved_recovery_sufficient:false},candidate_comparisons:[{candidate_id:'CAND-A',decision:'BLOCKED_PENDING_EVIDENCE_OR_RELEASE'},{candidate_id:'CAND-B',decision:'REJECTED_HARD_MISMATCH'}],
    qualification_graphs:[{candidate_id:'CAND-A',qualification_complete:'2026-10-07T02:00:00Z'}],simulation:{baseline_exposed_quantity:700},source_versions:[]};
  return {case:{case_id:'CASE-001',actions:[]},current,tool_trace:[{tool:'getExposure'},{tool:'findRecoveryOptions'},{tool:'EvidenceSpecialist'},{tool:'getQualificationDependencies'},{tool:'simulateRecovery'}],approvals:[],tasks:[],sources_current:true,latest_ai_review:null};
}
function saved(view) {
  view.latest_ai_review={case_version:1,case_hash:'old-hash',model:'test-model',facts:structuredClone(view.current),is_current:false,created_at:'2026-10-22T00:00:00Z',usage:{input_tokens:100,output_tokens:20},review:{summary:'Advisory',next_steps:['REQUEST_HUMAN_REVIEW']},
    tool_trace:[{sequence:1,tool:'getExposure',target:'CASE-001'},{sequence:2,tool:'getCandidateEvidence',target:'CAND-B'},{sequence:3,tool:'getCandidateEvidence',target:'CAND-A'},{sequence:4,tool:'finishReview',target:'CASE-001'}]};
  view.latest_ai_review.facts.exposure.shortage_date='old-date';
}
test('local flow shows code, fixture evidence, human gate and mock action separately',()=>{
  const nodes=workflow.build(fixture());
  assert.equal(nodes.length,9);
  assert.equal(nodes[3].owner,'Lokal / fixture');
  assert.equal(nodes[7].status,'HUMAN_GATE');
  assert.equal(nodes[8].status,'NOT_EXECUTED');
  assert.equal(nodes[8].output.production_release_authorized,false);
});
test('OpenAI flow has no fabricated execution when no result exists',()=>assert.equal(workflow.build(fixture(),'ai').length,0));
test('OpenAI trace preserves recorded model candidate order',()=>{
  const view=fixture();saved(view);
  const nodes=workflow.build(view,'ai');
  assert.equal(nodes.length,4);
  assert.equal(nodes[1].subtitle,'CAND-B');assert.equal(nodes[2].subtitle,'CAND-A');
  assert.equal(nodes[3].status,'ADVISORY');
});
test('archived AI node output uses the reviewed facts, not the latest case',()=>{
  const view=fixture();saved(view);
  const node=workflow.build(view,'ai')[0];
  assert.equal(node.context.case_version,1);assert.equal(node.context.case_hash,'old-hash');
  assert.equal(node.output.shortage_date,'old-date');
});
test('render escapes model prose and warns when review is outdated',()=>{
  const view=fixture();saved(view);view.latest_ai_review.review.summary='<script>alert(1)</script>';
  const html=workflow.render(view,{configured:true,model:'test-model'});
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('hanya arsip'));
});
test('review requires explicit cost acknowledgement and is disabled for stale sources',()=>{
  const view=fixture();view.sources_current=false;
  const html=workflow.render(view,{configured:true,model:'test-model'});
  assert.match(html,/id="ai-cost-consent" required disabled/);
  assert.match(html,/id="ai-review" disabled data-disabled="true"/);
});
test('replay and list/canvas controls do not imply live tool execution',()=>{
  const html=workflow.render(fixture(),{configured:false});
  assert.ok(html.includes('Replay hanya menelusuri catatan'));
  for(const id of ['flow-view','flow-fit','flow-plus','flow-minus','flow-prev','flow-next','flow-play','flow-inspector']) assert.ok(html.includes('id="'+id+'"'));
});
test('mobile replay scrolls the internal list to an offscreen late node',()=>{
  const list={scrollTop:0,clientHeight:530,getBoundingClientRect:()=>({top:100,bottom:630})};
  const button={getBoundingClientRect:()=>({top:1000,bottom:1132,height:132})};
  workflow.keepListNodeVisible(list,button);
  assert.equal(list.scrollTop,701);
});
test('already visible replay nodes do not move the internal list',()=>{
  const list={scrollTop:100,clientHeight:530,getBoundingClientRect:()=>({top:100,bottom:630})};
  const button={getBoundingClientRect:()=>({top:150,bottom:282,height:132})};
  workflow.keepListNodeVisible(list,button);
  assert.equal(list.scrollTop,100);
});
test('previous replay step scrolls backward without calling page scrolling APIs',()=>{
  const list={scrollTop:900,clientHeight:530,getBoundingClientRect:()=>({top:100,bottom:630})};
  const button={getBoundingClientRect:()=>({top:-100,bottom:32,height:132})};
  workflow.keepListNodeVisible(list,button);
  assert.equal(list.scrollTop,501);
});
