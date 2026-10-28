const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const sandbox = {document:{querySelector:()=>({})}};
const source = fs.readFileSync(path.join(__dirname,'../../apps/web/app.js'),'utf8');
vm.runInNewContext(source.split("window.addEventListener('hashchange'")[0] + ';this.ROLE_GUIDE=ROLE_GUIDE;this.setSession=value=>{session=value;};', sandbox);
const dashboard = ()=>({generated_at:'2026-10-28T00:00:00Z', data_mode:'SYNTHETIC_FIXTURES',
  cases:[{case_id:'CASE-001',case_version:1,material_id:'MAT-BRG-001',status:'UNDER_REVIEW',shortage_date:'2026-10-04',usable_stock:300,
    exposed_quantity:700,exposed_order_count:7,approved_covered_quantity:0,required_quantity:700,qualification_tasks_created:0,sources_current:true,
    candidates:[{candidate_id:'CAND-B',decision:'REJECTED_HARD_MISMATCH'}],top_scenario:{name:'Original expedite',state:'FEASIBLE',rank_reason:'Melindungi semua order'}}],
  notifications:[{case_id:'CASE-001',material_id:'MAT-BRG-001',severity:'CRITICAL',kind:'SHORTAGE',title:'<script>x</script>',detail:'700 EA'},
    {case_id:'CASE-001',material_id:'MAT-BRG-001',severity:'INFORMATION',kind:'RELEASE_BLOCKED',title:'Production release terblokir',detail:'Manusia'}]});

test('every role card states what it can and cannot do, matching server permissions',()=>{
  const byKey = Object.fromEntries(sandbox.ROLE_GUIDE.map(role=>[role.key,role]));
  assert.deepEqual(Object.keys(byKey), ['public','quality','engineering','planner']);
  assert.match(byKey.planner.cannot.join(' '), /Approve qualification task/);
  assert.match(byKey.planner.can.join(' '), /resequencing/);
  for (const key of ['quality','engineering']) assert.match(byKey[key].cannot.join(' '), /resequencing/);
  const html = sandbox.roleCard(byKey.quality, true);
  assert.match(html, /data-login-role="quality"/);
  assert.match(sandbox.roleCard(byKey.public, true), /href="#public"/);
});
test('public dashboard escapes notification text and asks anonymous viewers to log in',()=>{
  sandbox.setSession(null);
  const html = sandbox.publicDashboardHTML(dashboard());
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /Login untuk review detail/);
  assert.match(html, /Ditolak · spesifikasi tidak sesuai/);
  assert.match(html, /<strong>1<\/strong><small>notifikasi aktif/);
});
test('signed-in viewers get a direct case link and their own role first in the guide',()=>{
  sandbox.setSession({user_id:'planner',role:'PRODUCTION_PLANNER'});
  assert.match(sandbox.publicDashboardHTML(dashboard()), /href="#cases\/CASE-001\/summary">Buka kasus/);
  const guide = sandbox.guideHTML();
  assert.ok(guide.indexOf('Production Planner') < guide.indexOf('Quality Engineer'));
  assert.match(guide, /Peran Anda/);
  sandbox.setSession(null);
  assert.doesNotMatch(sandbox.guideHTML(), /Peran Anda/);
});
