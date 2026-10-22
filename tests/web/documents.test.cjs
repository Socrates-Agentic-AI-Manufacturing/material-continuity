const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const sandbox = {document:{querySelector:()=>({})}};
const source = fs.readFileSync(path.join(__dirname,'../../apps/web/app.js'),'utf8');
vm.runInNewContext(source.split("window.addEventListener('hashchange'")[0], sandbox);
const revision = ()=>({document_id:'DS-CAND-A',revision:'2',revision_id:'PDF-test',candidate_id:'CAND-A',status:'TEXT_READY',uploaded_at:'2026-10-22T00:00:00Z',uploaded_by:'quality',sha256:'hash',pages:['Bore diameter 25 mm'],accepted_rows:[],active_revision_id:null,extraction:null});

test('PDF detail requires separate consent for paid extraction and authoritative activation',()=>{
  const html=sandbox.documentDetail(revision(),{configured:true,model:'test-model'},true);
  assert.match(html,/id="document-extract"/);
  assert.match(html,/type="checkbox" required/);
  assert.match(html,/Approval lama langsung diblokir/);
  assert.match(html,/evidence tersebut menjadi UNKNOWN/);
  assert.doesNotMatch(html,/checked/);
});
test('PDF proposal quote is escaped and evidence acceptance is unchecked by default',()=>{
  const item=revision();item.extraction={model:'test-model',usage:{},rows:[{property:'BORE_DIAMETER',value:'25',unit:'mm',page:1,applicability:'BEARING-SEAT-25MM',quote:'<img src=x onerror=alert(1)>'}]};
  const html=sandbox.documentDetail(item,{},true);
  assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img/);assert.doesNotMatch(html,/checked/);
  assert.match(html,/id="document-review"/);
});
test('planner has read access but no extraction, review submit or activation controls',()=>{
  const html=sandbox.documentDetail(revision(),{configured:true},false);
  assert.doesNotMatch(html,/id="document-extract"|id="document-activate"|Simpan review evidence/);
  assert.match(html,/Buka PDF asli/);
});
test('failed parse explains OCR limit and cannot offer a paid extraction',()=>{
  const item=revision();item.pages=[];item.error='PDF_NEEDS_OCR_OR_TEXT';
  const html=sandbox.documentDetail(item,{configured:true},true);
  assert.match(html,/OCR belum tersedia/);assert.doesNotMatch(html,/id="document-extract"/);
});
test('upload progress clears on rejection and successful completion',async()=>{
  const node={hidden:true,isConnected:true};
  await assert.rejects(sandbox.withProgress(node,async()=>{assert.equal(node.hidden,false);throw new Error('revision immutable');}),/revision immutable/);
  assert.equal(node.hidden,true);
  assert.equal(await sandbox.withProgress(node,async()=>42),42);
  assert.equal(node.hidden,true);
});
test('progress cleanup leaves a detached old form alone after navigation',async()=>{
  const node={hidden:true,isConnected:true};
  await sandbox.withProgress(node,async()=>{node.isConnected=false;});
  assert.equal(node.hidden,false);
});
