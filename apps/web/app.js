/* Backend-connected synthetic review workflow. No business decisions in JS. */
let session = null;
let view = null;
let documents = [];
let busy = false;
let routePending = false;
let workflowCleanup = null;
let workflowPreferAI = false;
let llmStatus = {configured:false};
const content = document.querySelector('#content');
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const badge = value => `<span class="badge ${escape(value)}">${escape(value)}</span>`;
const time = value => value ? new Intl.DateTimeFormat('id-ID', {dateStyle:'medium', timeStyle:'short', timeZone:'Asia/Jakarta'}).format(new Date(value)) + ' WIB' : 'Belum diketahui';
const date = value => value || 'Belum diketahui';
const table = (caption, headers, rows) => `<div class="table-scroll"><table><caption>${escape(caption)}</caption><thead><tr>${headers.map(h=>`<th scope="col">${escape(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;

function notify(message, error = false) {
  const node = document.querySelector('#message');
  node.textContent = message;
  node.classList.toggle('error', error);
  node.hidden = false;
}

async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? {} : {'Content-Type':'application/json', 'X-CSRF-Token':session?.csrf_token || ''},
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'same-origin',
  });
  const data = await response.json();
  if (!response.ok) {
    const extra = data.error?.details?.reasons?.join(', ');
    const error = new Error(`${data.error?.message || 'Request gagal.'}${extra ? ' (' + extra + ')' : ''}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

async function perform(action) {
  if (busy) return;
  busy = true;
  document.querySelectorAll('button').forEach(button=>button.disabled = true);
  content.setAttribute('aria-busy', 'true');
  try { await action(); }
  catch(error) {
    notify(error.message, true);
    if (error.status === 401) { session = null; showLogin(); }
    else if (error.status === 409) { await route(); }
  } finally {
    busy = false;
    content.removeAttribute('aria-busy');
    document.querySelectorAll('button').forEach(button=>button.disabled = button.dataset.disabled === 'true');
    if (routePending) { routePending = false; perform(route); }
  }
}

function showLogin() {
  if (workflowCleanup) { workflowCleanup(); workflowCleanup = null; }
  document.querySelector('#navigation').hidden = true;
  document.querySelector('#identity').textContent = '';
  content.innerHTML = `<section class="panel login"><h1>Login untuk review kasus</h1>
    <p>Gunakan akun demo lokal. Role disimpan oleh server dan menentukan tindakan yang boleh disetujui.</p>
    <form id="login"><div><label for="username">Akun demo</label><select id="username" name="username">
      <option value="quality">quality — Quality Engineer</option><option value="engineering">engineering — Engineering Reviewer</option><option value="planner">planner — Production Planner</option>
    </select></div><div><label for="password">Password</label><input id="password" name="password" type="password" required autocomplete="current-password"></div>
    <button type="submit">Login</button></form>
    <small>Password default untuk demo localhost: <code>local-demo</code>. Jika diganti saat server dijalankan, gunakan password yang dikonfigurasi.</small></section>`;
  document.querySelector('#login').addEventListener('submit', event=>{
    event.preventDefault();
    const form = new FormData(event.target);
    perform(async()=>{
      session = await api('/api/login', {username:form.get('username'), password:form.get('password')});
      notify('Login berhasil.');
      await route();
    });
  });
}

function shell(section) {
  document.querySelector('#navigation').hidden = false;
  document.querySelector('#identity').innerHTML = `<div class="actions"><span>${escape(session.user_id)} · ${escape(session.role)}</span><button id="logout" class="secondary">Logout</button></div>`;
  document.querySelector('#logout').onclick = ()=>perform(async()=>{
    await api('/api/logout', {}); session = null; showLogin(); notify('Logout berhasil.');
  });
  document.querySelectorAll('#navigation a').forEach(link=>{
    if (link.hash === '#' + section) link.setAttribute('aria-current','page');
    else link.removeAttribute('aria-current');
  });
}

async function route() {
  if (workflowCleanup) { workflowCleanup(); workflowCleanup = null; }
  if (!session) { showLogin(); return; }
  const parts = (location.hash || '#overview').slice(1).split('/');
  const section = ['overview','cases','documents'].includes(parts[0]) ? parts[0] : 'overview';
  shell(section);
  if (section === 'documents') return showDocuments();
  if (section === 'cases' && parts[1]) return showCase(parts[1], parts[2] || 'summary');
  const data = await api('/api/cases');
  const cases = data.cases;
  content.innerHTML = `<h1>${section === 'overview' ? 'Overview' : 'Recovery Cases'}</h1>
    <p>${section === 'overview' ? 'Lihat risiko material dan buka kasus untuk menilai opsi pemulihan produksi.' : 'Kasus disimpan di backend. Buka kasus untuk melihat evidence dan melakukan review.'}</p>
    <p class="notice">Skenario fixture menggunakan tanggal September–Oktober 2026. Ini bukan status produksi real-time.</p>
    ${cases.length ? table('Kasus material', ['Kasus','Material','Shortage','Dampak produksi','Status','Terakhir diperbarui'], cases.map(item=>`<tr>
      <td><a href="#cases/${encodeURIComponent(item.case_id)}/summary">${escape(item.case_id)}</a><small>Versi ${item.case_version}</small></td>
      <td>${escape(item.material_id)}</td><td>${escape(date(item.shortage_date))}</td>
      <td>${item.exposed_quantity} EA / ${item.exposed_order_count} orders</td><td>${badge(item.status)}</td><td>${time(item.updated_at)}</td></tr>`)) : '<p>Belum ada kasus. Periksa inisialisasi fixture di server.</p>'}`;
}

async function showDocuments() {
  const data = await api('/api/documents');
  documents = data.documents;
  content.innerHTML = `<h1>Documents &amp; Data</h1><p>Corpus bukti sintetis yang dipakai dalam review. Dokumen dapat dibuka; extraction saat ini berasal dari prepared fixtures.</p>
    <p class="notice">Upload PDF, automatic extraction, dan sinkronisasi eksternal belum tersedia pada tahap ini.</p>
    ${table('Dokumen technical / quality', ['Dokumen','ID / Owner','Revisi','Effective date','Halaman','Checksum'], documents.map(item=>`<tr>
      <td><a href="/documents/${encodeURIComponent(item.filename)}" target="_blank" rel="noopener">${escape(item.filename)}</a></td>
      <td>${escape(item.document_id)}<small>${escape(item.owner)}</small></td><td>${escape(item.revision)}</td><td>${escape(item.effective_date)}</td><td>${item.page_count}</td>
      <td>${badge(item.checksum_valid ? 'MATCH' : 'MISMATCH')}</td></tr>`))}`;
}

const snapshot = ()=>({case_version:view.current.case_version, case_hash:view.current.case_hash});
const caseURL = ()=>'/api/cases/' + encodeURIComponent(view.case.case_id);

async function showCase(caseId, tab) {
  if (workflowCleanup) { workflowCleanup(); workflowCleanup = null; }
  [view, documents, llmStatus] = await Promise.all([
    api('/api/cases/' + encodeURIComponent(caseId)),
    api('/api/documents').then(data=>data.documents),
    api('/api/llm/status'),
  ]);
  const current = view.current;
  const tabs = [['summary','Summary & Options'],['workflow','Agent Workflow'],['evidence','Evidence Review'],['scenarios','Recovery Scenarios'],['approvals','Approval & Actions']];
  if (!tabs.some(([key])=>key===tab)) tab='summary';
  content.innerHTML = `<div class="case-heading"><div><a href="#cases">Kembali ke daftar kasus</a><h1>${escape(caseId)} · ${escape(current.exposure.material_id)}</h1><p class="muted">Versi ${current.case_version} · ${badge(current.status)} · diperbarui ${time(view.case.updated_at)}</p></div>
    <button id="investigate">Investigasi ulang</button></div>
    ${!view.sources_current ? '<p class="notice danger">Sumber berubah sejak review terakhir. Investigasi ulang diperlukan sebelum approval atau tindakan.</p>' : ''}
    <p><strong>Production release: BLOCKED.</strong> Approval qualification task tidak mengizinkan material dipakai di produksi.</p>
    <nav class="tabs" aria-label="Bagian kasus">${tabs.map(([key,label])=>`<a href="#cases/${encodeURIComponent(caseId)}/${key}" ${key===tab ? 'aria-current="page"' : ''}>${label}</a>`).join('')}</nav>
    <section id="case-tab">${tab==='workflow' ? AgentWorkflow.render(view,llmStatus) : ({summary:summaryTab, evidence:evidenceTab, scenarios:scenariosTab, approvals:approvalsTab}[tab])()}</section>
    <details><summary>Riwayat versi dan aktivitas investigasi</summary>${audit()}</details>`;
  document.querySelector('#investigate').onclick = ()=>perform(async()=>{
    const result = await api(caseURL() + '/investigate', snapshot());
    await route();
    notify(result.version_changed ? 'Investigasi selesai. Versi baru dibuat; approval sebelumnya perlu direview ulang.' : 'Investigasi selesai. Tidak ada perubahan decision state; versi tetap sama.');
  });
  if (tab === 'workflow') {
    workflowCleanup = AgentWorkflow.mount(document.querySelector('.workflow'), view, {preferAI:workflowPreferAI});
    document.querySelector('#ai-review-form').addEventListener('submit', event=>{
      event.preventDefault();
      if (!event.target.reportValidity()) return;
      perform(async()=>{
        if (workflowCleanup) { workflowCleanup(); workflowCleanup = null; }
        const progress = document.querySelector('#ai-review-progress');
        const errorBox = document.querySelector('#ai-review-error');
        errorBox.hidden = true;
        progress.hidden = false;
        progress.textContent = 'OpenAI sedang mereview snapshot kasus. Jejak aktual akan tersedia setelah selesai; canvas di bawah tetap menunjukkan catatan sebelumnya.';
        try {
          await api(caseURL() + '/ai-review', snapshot());
          workflowPreferAI = true;
          await showCase(caseId, 'workflow');
          notify('Review OpenAI selesai dan tersimpan. Advisory tidak mengubah approval atau production release.');
        } catch(error) {
          progress.hidden = true;
          errorBox.textContent = error.message + ' Tidak ada retry otomatis. Catatan sebelumnya tetap tersedia.';
          errorBox.hidden = false;
          workflowCleanup = AgentWorkflow.mount(document.querySelector('.workflow'), view, {preferAI:workflowPreferAI});
          throw error;
        }
      });
    });
  }
  const approveForm = document.querySelector('#approve');
  if (approveForm) approveForm.addEventListener('submit', event=>{
    event.preventDefault();
    const target = view.qualification_targets[Number(new FormData(event.target).get('target'))];
    perform(async()=>{
      await api(caseURL() + '/approvals', {...snapshot(), candidate_id:target.candidate_id, requirement_id:target.requirement_id});
      await route(); notify('Approval tersimpan untuk versi dan qualification target yang direview.');
    });
  });
  document.querySelectorAll('[data-execute]').forEach(button=>button.onclick = ()=>perform(async()=>{
    const result = await api(caseURL() + '/qualification-tasks', {...snapshot(), approval_id:button.dataset.execute});
    await route(); notify(`Mock QMS task ${result.task.qms_task_id} berhasil dibuat. Production release tetap blocked.`);
  }));
}

function summaryTab() {
  const c = view.current;
  const exposure = c.exposure;
  const options = c.recovery_options;
  return `<dl class="facts">
    <div><dt>Stok usable</dt><dd>${exposure.current_usable_stock} EA</dd></div><div><dt>Shortage pertama</dt><dd>${escape(date(exposure.shortage_date))}</dd></div>
    <div><dt>Produksi exposed</dt><dd>${c.simulation.baseline_exposed_quantity} EA / ${c.simulation.baseline_exposed_order_count} orders</dd></div>
    <div><dt>Timely approved coverage</dt><dd>${options.approved_covered_quantity} dari ${options.required_quantity} EA</dd></div><div><dt>Approved recovery cukup?</dt><dd>${options.approved_recovery_sufficient ? 'Ya' : 'Belum'}</dd></div>
    <div><dt>As-of skenario</dt><dd>${time(exposure.as_of)}</dd></div></dl>
    <h2>Approved recovery diperiksa terlebih dahulu</h2>
    ${table('Urutan pencarian recovery', ['Kategori','Opsi dievaluasi','Hasil'], options.search_trace.map(step=>`<tr><td>${escape(step.category)}</td><td>${escape(step.evaluated_option_ids.join(', ') || 'Tidak ada')}</td><td>${badge(step.outcome)}</td></tr>`))}
    <h2>Kandidat alternatif</h2>
    ${table('Availability bukan readiness', ['Kandidat','ETA','Tiba sebelum shortage?','Quantity','Hasil review'], options.unqualified_candidates.map(option=>{
      const comparison = c.candidate_comparisons.find(item=>item.candidate_id===option.candidate_id);
      return `<tr><td>${escape(option.candidate_id)}</td><td>${escape(option.ready_date)}</td><td>${option.arrives_by_need ? 'Ya' : 'Tidak'}</td><td>${option.available_quantity} EA</td><td>${badge(comparison?.decision || 'UNKNOWN')}</td></tr>`;
    }))}
    <h2>Production orders terdampak</h2>
    ${table('Dampak baseline sebelum recovery', ['Order','Assembly','Scheduled','Required','Unserved'], exposure.affected_orders.map(order=>`<tr><td>${escape(order.order_id)}</td><td>${escape(order.product_id)}</td><td>${escape(order.scheduled_date)}</td><td>${order.required_material_quantity} EA</td><td>${order.unserved_quantity} EA</td></tr>`))}`;
}

function sourceLink(source) {
  const known = documents.some(item=>item.filename===source.source_document);
  const label = `${escape(source.source_document)} · Rev ${escape(source.source_revision)} · p.${escape(source.source_page)}`;
  const page = /^\d+$/.test(source.source_page) ? '#page=' + source.source_page : '';
  return `<span class="source">${known ? `<a href="/documents/${encodeURIComponent(source.source_document)}${page}" target="_blank" rel="noopener">${label}</a>` : label}<small>${escape(source.source_location)} · ${escape(source.applicability)}</small></span>`;
}

function evidenceTab() {
  return `<h2>Requirement-level evidence</h2><p>Setiap status berasal dari comparison backend. Bukti yang belum cukup tetap UNKNOWN.</p>${view.current.candidate_comparisons.map(candidate=>`
    <h3>${escape(candidate.candidate_id)} · ${badge(candidate.decision)}</h3>
    ${table('Evidence ' + candidate.candidate_id, ['Requirement','Dibutuhkan','Observed','Status / alasan','Sumber'], candidate.rows.map(row=>`<tr>
      <td>${escape(row.requirement_name)}<small>${escape(row.requirement_id)}</small></td><td>${escape(row.required_operator)} ${escape(row.required_value)} ${escape(row.required_unit || '')}</td>
      <td>${row.observed_value===null ? 'Belum diketahui' : escape(row.observed_value)} ${escape(row.observed_unit || '')}</td><td>${badge(row.status)}<small>${escape(row.reason)}</small></td>
      <td>${row.evidence.length ? row.evidence.map(sourceLink).join('') : 'Tidak ada applicable evidence'}</td></tr>`))}`).join('')}`;
}

function scenariosTab() {
  const c = view.current;
  return `<h2>Perbandingan recovery</h2><p>Feasibility berdasarkan timeline dan coverage; setiap opsi masih membutuhkan otorisasi tindakan yang sesuai.</p>
    ${table('Biaya dalam unit moneter simulasi; currency belum ditentukan', ['Opsi','Siap (WIB)','Protected','Sisa exposed','Biaya tambahan','State'], c.simulation.scenarios.map(item=>`<tr>
      <td>${escape(item.name)}</td><td>${time(item.ready_at)}<small>${item.ready_by_shortage===null ? 'Timing unresolved' : item.ready_by_shortage ? 'Siap paling lambat saat shortage' : 'Siap setelah shortage'}</small></td>
      <td>${item.protected_quantity} EA</td><td>${item.remaining_exposed_quantity} EA / ${item.remaining_exposed_order_count} orders</td><td>${(item.incremental_cost_cents / 100).toLocaleString('id-ID')}</td><td>${badge(item.state)}<small>${escape(item.unresolved_conditions.join('; '))}</small></td></tr>`))}
    <h2>Qualification timeline</h2><p>Shortage: ${time(c.simulation.shortage_at)}. Ini jadwal qualification, bukan hasil test yang sudah lulus.</p>
    ${c.qualification_graphs.map(graph=>`<h3>${escape(graph.candidate_id)} · selesai terjadwal ${time(graph.qualification_complete)}</h3>
      ${table('Task dependencies ' + graph.candidate_id, ['Task','Mulai','Selesai','Durasi kerja','Dependency / resource'], graph.schedules.map(task=>`<tr><td>${escape(task.name)}<small>${badge(task.status)}</small></td><td>${time(task.start_time)}</td><td>${time(task.end_time)}</td><td>${escape(task.duration_hours ?? 'Unknown')} jam</td><td>${escape(task.predecessor_ids.join(', ') || 'Tidak ada')}<small>${escape(task.required_resource || 'Tanpa resource kalender')}</small></td></tr>`))}`).join('') || '<p>Qualification plan belum tersedia.</p>'}`;
}

function approvalsTab() {
  const targets = view.qualification_targets;
  const mayApprove = view.can_approve && view.sources_current && targets.length;
  return `<h2>Review dan authorization</h2><p>Approval mengizinkan pembuatan satu mock qualification task untuk target dan case version yang direview. Ini tidak memberikan production release.</p>
    ${mayApprove ? `<form id="approve" class="panel"><div><label for="target">Qualification target</label><select id="target" name="target">${targets.map((item,index)=>`<option value="${index}">${escape(item.candidate_id)} · ${escape(item.task_name)} · ${escape(item.requirement_id)}</option>`).join('')}</select></div><p>Anda menyetujui Case Version ${view.current.case_version}. Approval berlaku 8 jam.</p><button type="submit">Approve qualification task</button></form>` : `<p class="notice">${!view.can_approve ? 'Role Anda tidak dapat menyetujui qualification task. Login sebagai Engineering Reviewer atau Quality Engineer.' : !view.sources_current ? 'Sumber berubah. Investigasi ulang sebelum approval.' : 'Tidak ada qualification target yang berlaku.'}</p>`}
    <h3>Approval records</h3>
    ${view.approvals.length ? table('Authorization bound to case version', ['Approval / target','Reviewer','Versi','Berlaku sampai','Pemeriksaan','Tindakan'], view.approvals.map(item=>`<tr>
      <td>${escape(item.approval_id)}<small>${escape(item.scope.candidate_id)} · ${escape(item.scope.requirement_id)}</small></td><td>${escape(item.approver_id)}<small>${escape(item.approver_role)}</small></td>
      <td>${item.case_version}</td><td>${time(item.expires_at)}</td><td>${badge(item.validation.status)}<small>${escape(item.validation.reasons.join(', '))}</small></td>
      <td><button class="secondary" data-execute="${escape(item.approval_id)}" ${item.validation.status!=='AUTHORIZED' ? 'disabled data-disabled="true"' : ''}>Create mock QMS task</button></td></tr>`)) : '<p>Belum ada approval. Review bukti dan skenario sebelum menyetujui qualification task.</p>'}
    <h3>Qualification tasks &amp; receipts</h3>
    ${view.tasks.length ? table('Mock QMS tasks tersimpan', ['QMS ID','Kandidat / requirement','Task','Dibuat','Status'], view.tasks.map(task=>`<tr><td>${escape(task.qms_task_id)}</td><td>${escape(task.candidate_id)}<small>${escape(task.requirement_id)}</small></td><td>${escape(task.task_name)}</td><td>${time(task.created_at)}</td><td>${badge(task.status)}</td></tr>`)) : '<p>Belum ada QMS task yang dibuat.</p>'}
    ${view.case.actions.map(action=>`<details><summary>Receipt ${escape(action.external_reference)}</summary><dl><dt>Action</dt><dd>${escape(action.action_id)}</dd><dt>Reviewed version</dt><dd>${action.case_version}</dd><dt>Case hash</dt><dd><code>${escape(action.case_hash)}</code></dd><dt>Idempotency key</dt><dd><code>${escape(action.idempotency_key)}</code></dd></dl></details>`).join('')}`;
}

function audit() {
  return table('Immutable case versions', ['Version','Dibuat','Reason','Hash'], view.case.versions.map(version=>`<tr><td>${version.case_version}</td><td>${time(version.created_at)}</td><td>${escape(version.change_reason)}</td><td><code>${escape(version.case_hash)}</code></td></tr>`)) +
    table('Aktivitas investigasi terakhir', ['Urutan','Tool','Target','Hasil'], view.tool_trace.map(step=>`<tr><td>${step.sequence}</td><td>${escape(step.tool)}</td><td>${escape(step.target)}</td><td>${escape(step.outcome)}</td></tr>`));
}

window.addEventListener('hashchange', ()=>{
  if (busy) routePending = true;
  else perform(route);
});
perform(async()=>{
  try { session = await api('/api/session'); }
  catch(error) { if(error.status!==401) throw error; }
  await route();
});
