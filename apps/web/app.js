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
const STATUS_LABELS = {
  UNDER_REVIEW:'Perlu ditinjau', MATCH:'Sesuai', MISMATCH:'Tidak sesuai',
  BLOCKED:'Terblokir', REJECTED_HARD_MISMATCH:'Ditolak · spesifikasi tidak sesuai',
  BLOCKED_PENDING_EVIDENCE_OR_RELEASE:'Menunggu bukti / release', UNKNOWN:'Belum diketahui',
  FOUND:'Ditemukan', NONE:'Tidak ada', FEASIBLE:'Layak', AUTHORIZED:'Diizinkan',
  PARTIAL:'Sebagian', UNRESOLVED:'Belum selesai', TEXT_READY:'Siap direview',
  HUMAN_GATE:'Persetujuan manusia', RECORDED:'Terekam', VERSIONED:'Terversi',
  RECEIPT_RECORDED:'Receipt tersimpan', NOT_EXECUTED:'Belum dijalankan', ADVISORY:'Advisory',
};
const statusTone = value => ['MATCH','FEASIBLE','AUTHORIZED','FOUND','RECEIPT_RECORDED'].includes(value) ? 'positive'
  : ['MISMATCH','BLOCKED','REJECTED_HARD_MISMATCH'].includes(value) ? 'negative'
  : ['UNKNOWN','PARTIAL','UNRESOLVED','BLOCKED_PENDING_EVIDENCE_OR_RELEASE','UNDER_REVIEW','HUMAN_GATE'].includes(value) ? 'critical'
  : ['ADVISORY'].includes(value) ? 'advisory' : 'neutral';
const badge = value => `<span class="badge ${statusTone(value)} ${escape(value)}" title="${escape(value)}">${escape(STATUS_LABELS[value] || String(value).replaceAll('_',' ').toLowerCase())}</span>`;
const ROLE_LABELS = {QUALITY_ENGINEER:'Quality Engineer',ENGINEERING_REVIEWER:'Engineering Reviewer',PRODUCTION_PLANNER:'Production Planner'};
const roleLabel = value => ROLE_LABELS[value] || String(value || '').replaceAll('_',' ').toLowerCase();
const time = value => value ? new Intl.DateTimeFormat('id-ID', {dateStyle:'medium', timeStyle:'short', timeZone:'Asia/Jakarta'}).format(new Date(value)) + ' WIB' : 'Belum diketahui';
const date = value => value || 'Belum diketahui';
const table = (caption, headers, rows) => `<div class="table-scroll"><table><caption>${escape(caption)}</caption><thead><tr>${headers.map(h=>`<th scope="col">${escape(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
const JOULE_URL = 'https://aws-sap-hackathon-si4ykj9d.ap10.sapdas.cloud.sap/webclient/standalone/material_continuity_capability';

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

async function withProgress(node, action) {
  node.hidden = false;
  try { return await action(); }
  finally { if (node.isConnected) node.hidden = true; }
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

const ICONS = {
  bell:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 10a6 6 0 1 1 12 0v3.4l1.6 2.6H4.4L6 13.4Z"/><path d="M9.5 19a2.5 2.5 0 0 0 5 0"/></svg>',
  joule:'<svg class="ui5-icon-root" part="root" dir="ltr" viewBox="0 0 16 16" role="presentation" focusable="false" preserveAspectRatio="xMidYMid meet" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><g role="presentation"><path d="M12 0a.75.75 0 0 1 .62.326l3.25 4.752a.75.75 0 0 1-.018.871l-7.25 9.753a.756.756 0 0 1-1.204 0L.148 5.95a.75.75 0 0 1-.017-.871L3.437.254A.75.75 0 0 1 4 0h8ZM1.67 5.484 8 13.998l6.328-8.514L11.605 1.5h-7.21L1.671 5.484Zm7.5-2.25a.35.35 0 0 1 .66 0c.37 1.084.85 1.575 1.93 1.937.32.11.32.562 0 .662-1.08.371-1.57.853-1.93 1.936a.35.35 0 0 1-.66 0c-.37-1.083-.85-1.575-1.93-1.936-.32-.11-.32-.562 0-.662 1.08-.372 1.57-.853 1.93-1.937Z"></path></g></svg>',
  menu:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
  help:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M9.6 9.6a2.5 2.5 0 1 1 3.3 2.4c-.6.2-.9.8-.9 1.4v.6"/><path d="M12 16.8v.2"/></svg>',
  person:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8.5" r="3.5"/><path d="M5 19.5a7 7 0 0 1 14 0"/></svg>',
};
const SEVERITY = {
  CRITICAL:['negative','Kritis'], NEGATIVE:['negative','Ditolak'], WARNING:['critical','Perhatian'], INFORMATION:['information','Info'],
};
const ROLE_GUIDE = [
  {key:'public', title:'Publik', username:null, tagline:'Memantau risiko material tanpa login.',
    can:['Melihat dashboard ringkas dan notifikasi risiko','Melihat status kandidat dan rekomendasi skenario teratas'],
    cannot:['Membuka detail bukti dan dokumen','Memberi approval atau membuat tindakan'],
    flow:[['Buka dashboard publik','Lihat kapan stok habis dan berapa produksi terdampak.','#public'],['Cek notifikasi','Klik ikon lonceng untuk melihat risiko yang perlu ditindaklanjuti.','#public'],['Login bila perlu detail','Gunakan akun sesuai peran untuk review bukti dan approval.','#login']]},
  {key:'quality', title:'Quality Engineer', username:'quality', tagline:'Penjaga mutu: memastikan bukti dan uji kualifikasi sah.',
    can:['Upload, ekstrak, review, dan aktifkan PDF bukti kandidat','Approve qualification task lalu membuat mock QMS task','Inject delayed delivery dan investigasi ulang kasus'],
    cannot:['Approve production resequencing','Merilis material ke produksi'],
    flow:[['Pantau risiko','Overview menunjukkan shortage terdekat dan approval yang menunggu.','#overview'],['Periksa bukti kandidat','Evidence Review: MATCH, MISMATCH, atau UNKNOWN per requirement, lengkap dengan halaman sumber.','#cases/CASE-001/evidence'],['Perbarui dokumen bukti','Documents & Data: upload revisi datasheet, review klaim, lalu aktifkan revisi.','#documents'],['Investigasi ulang','Kembali ke kasus dan tekan Investigasi ulang agar versi kasus mengikuti bukti terbaru.','#cases/CASE-001/summary'],['Approve qualification','Approval & Actions: approve qualification task lalu buat mock QMS task.','#cases/CASE-001/approvals']]},
  {key:'engineering', title:'Engineering Reviewer', username:'engineering', tagline:'Ahli teknis: menilai kesesuaian spesifikasi kandidat.',
    can:['Menilai ukuran, beban, dan pelumas kandidat terhadap requirement','Upload, ekstrak, review, dan aktifkan PDF bukti kandidat','Approve qualification task lalu membuat mock QMS task'],
    cannot:['Approve production resequencing','Merilis material ke produksi'],
    flow:[['Buka kasus','Summary & Options: pahami exposure dan opsi approved yang sudah diperiksa.','#cases/CASE-001/summary'],['Bandingkan spesifikasi','Evidence Review: kandidat dengan hard mismatch otomatis ditolak.','#cases/CASE-001/evidence'],['Cek jadwal qualification','Recovery Scenarios: lihat kapan kandidat benar-benar siap, bukan hanya kapan tiba.','#cases/CASE-001/scenarios'],['Approve qualification','Approval & Actions: setujui uji untuk requirement yang belum terbukti.','#cases/CASE-001/approvals']]},
  {key:'planner', title:'Production Planner', username:'planner', tagline:'Perencana produksi: menjaga jadwal tetap berjalan.',
    can:['Inject delayed delivery dan investigasi ulang kasus','Approve production resequencing lalu membuat mock authorization','Membaca seluruh kasus, bukti, dan dokumen'],
    cannot:['Upload atau mengaktifkan dokumen bukti','Approve qualification task'],
    flow:[['Pantau risiko','Overview menunjukkan shortage terdekat dan order terdampak.','#overview'],['Simulasikan keterlambatan','Summary: inject delayed delivery untuk melihat dampak terhadap exposure.','#cases/CASE-001/summary'],['Bandingkan skenario','Recovery Scenarios: ranking berdasarkan coverage, waktu, dan biaya.','#cases/CASE-001/scenarios'],['Approve resequencing','Approval & Actions: setujui resequencing lalu buat mock authorization.','#cases/CASE-001/approvals']]},
];
const CASE_FLOW = ['Disruption terdeteksi','Hitung exposure','Cek opsi approved','Review bukti kandidat','Jadwal qualification','Bandingkan skenario','Approval manusia','Mock action receipt'];
let publicData = null;

function roleCard(role, withButton) {
  return `<article class="role-card role-${role.key}"><header><span class="role-icon" aria-hidden="true">${role.username ? escape(role.title.slice(0,1)) : ICONS.person}</span><div><h3>${escape(role.title)}</h3><small>${role.username ? 'Username: <code>' + escape(role.username) + '</code>' : 'Tanpa login'}</small></div></header>
    <p>${escape(role.tagline)}</p>
    <ul class="role-can">${role.can.map(item=>`<li>${escape(item)}</li>`).join('')}</ul>
    <ul class="role-cannot">${role.cannot.map(item=>`<li>${escape(item)}</li>`).join('')}</ul>
    ${withButton ? (role.username ? `<button type="button" class="secondary" data-login-role="${escape(role.username)}">Masuk sebagai ${escape(role.title)}</button>` : '<a class="button-link secondary" href="#public">Buka dashboard publik</a>') : ''}</article>`;
}

function showLogin() {
  if (workflowCleanup) { workflowCleanup(); workflowCleanup = null; }
  shell('login');
  content.innerHTML = `<section class="login-shell"><div class="login-context">
    <span class="eyebrow">Material continuity workspace</span>
    <h1>Keputusan pemulihan material yang dapat ditelusuri.</h1>
    <p>Satukan exposure produksi, bukti teknis, qualification plan, dan human approval dalam satu review workspace.</p>
    <div class="login-links"><a class="button-link" href="#guide">Panduan pengguna</a><a class="button-link secondary" href="#public">Lihat dashboard publik</a></div>
    <p class="login-safety">Demo · data sintetis · production release tetap dikendalikan manusia</p>
    </div><div class="panel login-card"><span class="eyebrow">Akses workspace</span><h2>Login untuk review kasus</h2>
    <p>Pilih peran sesuai tugas Anda. Hak tindakan ditentukan oleh server, bukan browser.</p>
    <form id="login"><div><label for="username">Peran demo</label><select id="username" name="username">
      <option value="quality">quality — Quality Engineer</option><option value="engineering">engineering — Engineering Reviewer</option><option value="planner">planner — Production Planner</option>
    </select></div><div><label for="password">Password</label><input id="password" name="password" type="password" required autocomplete="current-password"></div>
    <button type="submit">Masuk ke workspace <span aria-hidden="true">→</span></button></form>
    <small>Password demo: <code>local-demo</code></small></div></section>
    <section class="role-section" aria-labelledby="role-heading"><div class="section-heading"><div><span class="eyebrow">Siapa melakukan apa</span><h2 id="role-heading">Peran di Material Continuity</h2></div><p><a href="#guide">Lihat alur lengkap per peran →</a></p></div>
    <div class="role-grid">${ROLE_GUIDE.map(role=>roleCard(role, true)).join('')}</div></section>`;
  document.querySelector('#login').addEventListener('submit', event=>{
    event.preventDefault();
    const form = new FormData(event.target);
    perform(async()=>{
      session = await api('/api/login', {username:form.get('username'), password:form.get('password')});
      notify('Login berhasil.');
      if (location.hash === '#login') location.hash = '#overview';
      else await route();
    });
  });
  document.querySelectorAll('[data-login-role]').forEach(button=>button.addEventListener('click', ()=>{
    document.querySelector('#username').value = button.dataset.loginRole;
    document.querySelector('#password').focus();
    document.querySelector('.login-card').scrollIntoView({block:'center'});
  }));
}

function navItems() {
  return session
    ? [['overview','Overview'],['cases','Recovery Cases'],['documents','Documents & Data'],['public','Dashboard Publik'],['guide','Panduan']]
    : [['public','Dashboard Publik'],['guide','Panduan Pengguna'],['login','Login']];
}

function shell(section) {
  const items = navItems();
  const nav = document.querySelector('#navigation');
  nav.hidden = false;
  nav.innerHTML = items.map(([key,label])=>`<a href="#${key}" ${key===section ? 'aria-current="page"' : ''}>${label}</a>`).join('');
  document.querySelector('#shell-home').setAttribute('href', session ? '#overview' : '#public');
  const initial = escape(String(session?.user_id || '?').slice(0,1).toUpperCase());
  const profile = session
    ? `<button class="shell-avatar" type="button" data-popover="profile-popover" aria-expanded="false" aria-controls="profile-popover" aria-label="Profil ${escape(session.user_id)}">${initial}</button>
       <div class="popover profile-popover" id="profile-popover" role="dialog" aria-label="Profil" hidden><div class="popover-head"><span class="shell-avatar large" aria-hidden="true">${initial}</span><div><strong>${escape(session.user_id)}</strong><small>${escape(roleLabel(session.role))}</small></div></div>
       <a class="popover-item" href="#guide">Panduan peran saya</a><button id="logout" class="popover-item" type="button">Keluar</button></div>`
    : `<a class="shell-login" href="#login">Login</a>`;
  document.querySelector('#shell-actions').innerHTML = `
    <button class="shell-icon" type="button" id="shell-notifications" data-popover="notification-popover" aria-expanded="false" aria-controls="notification-popover" aria-label="Notifikasi">${ICONS.bell}<span class="shell-count" id="notification-count" hidden></span></button>
    <a class="shell-icon" href="${JOULE_URL}" target="_blank" rel="noopener noreferrer" aria-label="Joule Assistant">${ICONS.joule}</a>
    <div class="popover notification-popover" id="notification-popover" role="dialog" aria-label="Notifikasi" hidden><div class="popover-title"><strong>Notifikasi</strong><a href="#public">Lihat dashboard</a></div><div id="notification-list"><p class="popover-empty">Memuat notifikasi…</p></div></div>
    <button class="shell-icon" type="button" data-popover="menu-popover" aria-expanded="false" aria-controls="menu-popover" aria-label="Navigasi">${ICONS.menu}</button>
    <div class="popover menu-popover" id="menu-popover" role="dialog" aria-label="Navigasi" hidden><span class="popover-group">Navigasi</span>${items.map(([key,label])=>`<a class="popover-item" href="#${key}" ${key===section ? 'aria-current="page"' : ''}>${label}</a>`).join('')}</div>
    <a class="shell-icon" href="#guide" aria-label="Panduan pengguna" title="Panduan pengguna">${ICONS.help}</a>
    ${profile}`;
  const logout = document.querySelector('#logout');
  if (logout) logout.onclick = ()=>perform(async()=>{
    await api('/api/logout', {}); session = null; location.hash = '#login'; await route(); notify('Logout berhasil.');
  });
  // The public dashboard loads the same payload itself and then renders the bell.
  if (section !== 'public') refreshNotifications();
}

async function refreshNotifications() {
  try { publicData = await api('/api/public/dashboard'); }
  catch (error) { publicData = null; }
  renderNotifications();
}

function notificationItem(item) {
  const [tone,label] = SEVERITY[item.severity] || ['neutral','Info'];
  return `<li class="notification ${tone}"><span class="notification-dot" aria-hidden="true"></span><div><strong>${escape(item.title)}</strong><p>${escape(item.detail)}</p><small>${escape(label)} · ${escape(item.case_id)} · ${escape(item.material_id)}</small></div></li>`;
}

function renderNotifications() {
  const list = document.querySelector('#notification-list');
  const count = document.querySelector('#notification-count');
  const button = document.querySelector('#shell-notifications');
  if (!list || !count || !button) return;
  const items = publicData?.notifications || [];
  const urgent = items.filter(item=>item.severity !== 'INFORMATION').length;
  count.textContent = urgent > 9 ? '9+' : String(urgent);
  count.hidden = !urgent;
  button.setAttribute('aria-label', `Notifikasi, ${urgent} perlu perhatian`);
  list.innerHTML = publicData ? (items.length ? `<ul class="notification-list">${items.map(notificationItem).join('')}</ul>` : '<p class="popover-empty">Tidak ada notifikasi.</p>') : '<p class="popover-empty">Notifikasi tidak dapat dimuat.</p>';
}

function closePopovers(except) {
  document.querySelectorAll('.popover').forEach(panel=>{
    if (panel.id === except) return;
    panel.hidden = true;
    document.querySelector(`[data-popover="${panel.id}"]`)?.setAttribute('aria-expanded','false');
  });
}

function publicDashboardHTML(data) {
  const cases = data.cases;
  const first = cases[0];
  const totalExposed = cases.reduce((sum,item)=>sum + Number(item.exposed_quantity || 0),0);
  const totalOrders = cases.reduce((sum,item)=>sum + Number(item.exposed_order_count || 0),0);
  const urgent = data.notifications.filter(item=>item.severity !== 'INFORMATION');
  return `<section class="page-heading"><div><span class="eyebrow">Public monitoring</span><h1>Dashboard Material Continuity</h1>
      <p>Ringkasan risiko material untuk semua pihak. Detail bukti dan approval tersedia setelah login.</p></div>
      <span class="data-context">Data sintetis · diperbarui ${time(data.generated_at)}</span></section>
    <section class="metric-grid overview-metrics" aria-label="Ringkasan risiko publik">
      <article class="metric critical"><span>Stok habis</span><strong>${escape(date(first?.shortage_date))}</strong><small>shortage terdekat</small></article>
      <article class="metric critical"><span>Produksi terdampak</span><strong>${totalExposed.toLocaleString('id-ID')} <em>EA</em></strong><small>${totalOrders} production order</small></article>
      <article class="metric"><span>Approved coverage</span><strong>${first ? `${first.approved_covered_quantity} / ${first.required_quantity}` : '—'} <em>EA</em></strong><small>opsi approved yang tepat waktu</small></article>
      <article class="metric primary"><span>Perlu perhatian</span><strong>${urgent.length}</strong><small>notifikasi aktif</small></article></section>
    <div class="public-layout"><section class="public-panel" aria-labelledby="public-alerts"><div class="public-panel-head"><h2 id="public-alerts">Notifikasi</h2><span>${data.notifications.length} item</span></div>
      ${data.notifications.length ? `<ul class="notification-list">${data.notifications.map(notificationItem).join('')}</ul>` : '<p class="popover-empty">Tidak ada notifikasi.</p>'}</section>
    <div class="public-cases">${cases.map(item=>`<section class="public-panel" aria-label="Kasus ${escape(item.case_id)}"><div class="public-panel-head"><div><span class="eyebrow">${escape(item.case_id)} · Versi ${item.case_version}</span><h2>${escape(item.material_id)}</h2></div>${badge(item.status)}</div>
      <dl class="public-facts"><div><dt>Stok usable</dt><dd>${item.usable_stock} EA</dd></div><div><dt>Shortage</dt><dd>${escape(date(item.shortage_date))}</dd></div><div><dt>QMS task dibuat</dt><dd>${item.qualification_tasks_created}</dd></div><div><dt>Production release</dt><dd>${badge('BLOCKED')}</dd></div></dl>
      <h3>Kandidat pengganti</h3><ul class="candidate-chips">${item.candidates.map(candidate=>`<li><strong>${escape(candidate.candidate_id)}</strong>${badge(candidate.decision)}</li>`).join('')}</ul>
      ${item.top_scenario ? `<h3>Rekomendasi skenario teratas</h3><div class="top-scenario"><div><strong>${escape(item.top_scenario.name)}</strong>${badge(item.top_scenario.state)}</div><p>${escape(item.top_scenario.rank_reason)}</p></div>` : ''}
      ${!item.sources_current ? '<p class="notice danger">Sumber data berubah. Kasus perlu diinvestigasi ulang.</p>' : ''}
      <p class="public-cta">${session ? `<a class="button-link" href="#cases/${encodeURIComponent(item.case_id)}/summary">Buka kasus</a>` : '<a class="button-link" href="#login">Login untuk review detail</a>'}</p></section>`).join('') || '<div class="empty-state"><strong>Belum ada kasus aktif</strong></div>'}</div></div>`;
}

async function showPublicDashboard() {
  publicData = await api('/api/public/dashboard');
  renderNotifications();
  content.innerHTML = publicDashboardHTML(publicData);
}

function guideHTML() {
  const mine = session ? ROLE_GUIDE.find(role=>role.username===session.user_id) : null;
  const ordered = mine ? [mine, ...ROLE_GUIDE.filter(role=>role!==mine)] : ROLE_GUIDE;
  return `<section class="page-heading"><div><span class="eyebrow">User guide</span><h1>Panduan pengguna</h1>
      <p>Material Continuity membantu pabrik memutuskan apakah komponen pengganti dapat dipakai tepat waktu, dengan bukti yang dapat ditelusuri dan persetujuan manusia.</p></div>
      ${session ? `<span class="data-context">Login sebagai ${escape(roleLabel(session.role))}</span>` : '<a class="button-link" href="#login">Login</a>'}</section>
    <section class="public-panel"><div class="public-panel-head"><h2>Alur kasus</h2><span>Dari disruption sampai tindakan</span></div>
      <ol class="case-flow">${CASE_FLOW.map((step,index)=>`<li><span>${index+1}</span>${escape(step)}</li>`).join('')}</ol>
      <p class="muted">AI membaca dokumen dan menjelaskan. Kode menghitung dan menegakkan aturan. Manusia memberi approval. Production release selalu tetap di tangan manusia.</p></section>
    <div class="guide-roles">${ordered.map(role=>`<section class="public-panel guide-role ${role===mine ? 'is-mine' : ''}" aria-label="Panduan ${escape(role.title)}">
      ${role===mine ? '<span class="guide-mine">Peran Anda</span>' : ''}${roleCard(role, false)}
      <h3>Alur kerja</h3><ol class="guide-steps">${role.flow.map(([title,detail,link])=>`<li><a href="${link}"><strong>${escape(title)}</strong><span>${escape(detail)}</span></a></li>`).join('')}</ol></section>`).join('')}</div>`;
}

function showGuide() {
  content.innerHTML = guideHTML();
}

async function route() {
  if (workflowCleanup) { workflowCleanup(); workflowCleanup = null; }
  closePopovers();
  const parts = (location.hash || '#public').slice(1).split('/');
  if (parts[0] === 'public') { shell('public'); return showPublicDashboard(); }
  if (parts[0] === 'guide') { shell('guide'); return showGuide(); }
  if (!session) { showLogin(); return; }
  if (parts[0] === 'login') { location.hash = '#overview'; return; }
  const section = ['overview','cases','documents'].includes(parts[0]) ? parts[0] : 'overview';
  shell(section);
  if (section === 'documents') return showDocuments(parts[1]);
  if (section === 'cases' && parts[1]) return showCase(parts[1], parts[2] || 'summary');
  const data = await api('/api/cases');
  const cases = data.cases;
  const totalExposed = cases.reduce((sum,item)=>sum + Number(item.exposed_quantity || 0),0);
  const totalOrders = cases.reduce((sum,item)=>sum + Number(item.exposed_order_count || 0),0);
  const pendingApprovals = cases.reduce((sum,item)=>sum + Number(item.pending_approval_count || 0),0);
  const firstShortage = cases.map(item=>item.shortage_date).filter(Boolean).sort()[0];
  content.innerHTML = `<section class="page-heading"><div><span class="eyebrow">Operate · recovery control</span><h1>${section === 'overview' ? 'Continuity overview' : 'Recovery cases'}</h1>
    <p>${section === 'overview' ? 'Prioritaskan risiko material, lalu buka kasus untuk menilai jalur pemulihan.' : 'Telusuri kasus, bukti, keputusan, dan authorization yang tersimpan di backend.'}</p></div>
    <span class="data-context">Fixture · Sep–Okt 2026</span></section>
    <section class="metric-grid overview-metrics" aria-label="Ringkasan risiko"><article class="metric critical"><span>Stok habis</span><strong>${escape(date(firstShortage))}</strong><small>shortage terdekat</small></article>
      <article class="metric primary"><span>Approval menunggu</span><strong>${pendingApprovals}</strong><small>authorization operasional</small></article>
      <article class="metric"><span>Quantity exposed</span><strong>${totalExposed.toLocaleString('id-ID')} <em>EA</em></strong><small>baseline exposure</small></article>
      <article class="metric"><span>Production orders</span><strong>${totalOrders}</strong><small>order terdampak</small></article></section>
    <div class="section-heading"><div><span class="eyebrow">Prioritas saat ini</span><h2>Kasus material</h2></div><p>Pilih kasus untuk membuka decision workspace.</p></div>
    ${cases.length ? table('Kasus material aktif', ['Kasus','Material','Shortage','Dampak produksi','Status','Diperbarui'], cases.map(item=>`<tr>
      <td><a href="#cases/${encodeURIComponent(item.case_id)}/summary">${escape(item.case_id)}</a><small>Versi ${item.case_version}</small></td>
      <td>${escape(item.material_id)}</td><td>${escape(date(item.shortage_date))}</td>
      <td>${item.exposed_quantity} EA / ${item.exposed_order_count} orders</td><td>${badge(item.status)}</td><td>${time(item.updated_at)}</td></tr>`)) : '<p>Belum ada kasus. Periksa inisialisasi fixture di server.</p>'}`;
}

async function showDocuments(revisionId) {
  const [data, status] = await Promise.all([api('/api/documents'), api('/api/llm/status')]);
  documents = data.documents;
  const canEdit = ['QUALITY_ENGINEER','ENGINEERING_REVIEWER'].includes(session.role);
  const item = revisionId ? await api('/api/document-revisions/' + encodeURIComponent(revisionId)) : null;
  content.innerHTML = `<section class="page-heading"><div><span class="eyebrow">Evidence library</span><h1>Documents &amp; Data</h1><p>Kelola sumber bukti, revisi, dan authority tanpa mencampurkan proposal AI dengan evidence terverifikasi.</p></div>
    <div class="quick-links"><a href="#cases/CASE-001/evidence">Evidence CASE-001</a><a href="#cases/CASE-001/approvals">Approval &amp; Actions</a></div></section>
    <div class="context-banner"><strong>Batas sistem saat ini</strong><span>PDF dibaca per halaman. Internet dan OCR belum terhubung. Ekstraksi OpenAI hanya menghasilkan usulan.</span></div>
    ${item ? documentDetail(item, status, canEdit) : ''}
    ${canEdit ? `<details class="upload-disclosure"><summary><span><strong>Upload revisi PDF kandidat</strong><small>Simpan dan baca sumber baru secara lokal</small></span><span aria-hidden="true">＋</span></summary><form id="upload-document" class="panel upload-panel">
      <div><label for="doc-candidate">Kandidat</label><select id="doc-candidate" name="candidate_id">${['CAND-A','CAND-B','CAND-C'].map(id=>`<option>${id}</option>`).join('')}</select></div>
      <div><label for="doc-id">Document ID stabil antar revisi</label><input id="doc-id" name="document_id" value="DS-CAND-A" pattern="(?:[A-Za-z0-9._]|-){1,60}" required maxlength="60"></div>
      <div><label for="doc-revision">Revisi sesuai isi PDF</label><input id="doc-revision" name="revision" placeholder="Contoh: 2 atau 3" pattern="(?:[A-Za-z0-9._]|-){1,60}" required maxlength="60"></div>
      <div><label for="doc-file">PDF berbasis teks (maks. 2 MB / 20 halaman)</label><input id="doc-file" name="file" type="file" accept="application/pdf,.pdf" required></div>
      <p>Upload hanya menyimpan dan membaca teks secara lokal. Tidak mengirim ke OpenAI atau mengaktifkan revisi. Gunakan ID yang sama untuk revisi dokumen yang sama; isi revisi lama tidak bisa ditimpa.</p>
      <button type="submit">Upload dan baca PDF</button><p id="upload-progress" role="status" hidden>Menyimpan dan membaca halaman PDF…</p></form></details>` : '<p class="notice">Planner dapat membaca dokumen. Upload, review evidence, dan aktivasi memerlukan Engineering atau Quality.</p>'}
    <div class="section-heading"><div><span class="eyebrow">Revision authority</span><h2>Revisi tersimpan</h2></div></div>${data.revisions.length ? table('Revisi PDF lokal; pilih detail untuk ekstraksi dan review', ['Dokumen / kandidat','Revisi','Proses','Authority'], data.revisions.map(row=>`<tr><td><a href="#documents/${escape(row.revision_id)}">${escape(row.original_name)}</a><small>${escape(row.document_id)} · ${escape(row.candidate_id)}</small></td><td>${escape(row.revision)}</td><td>${badge(row.status)}<small>${escape(row.error || '')}</small></td><td>${row.active ? '<span class="authority-active">Aktif</span>' : 'Arsip / belum aktif'}<small>${row.reviewed_by ? 'Direview ' + escape(row.reviewed_by) : 'Evidence belum direview'}</small></td></tr>`)) : '<div class="empty-state"><strong>Belum ada PDF yang diupload</strong><p>Corpus awal masih memakai prepared evidence sampai dossier kandidat diaktifkan.</p></div>'}
    <div class="section-heading"><div><span class="eyebrow">Prepared corpus</span><h2>Corpus dan sumber bukti</h2></div><p>${documents.length} dokumen technical / quality</p></div>
    ${table('Dokumen technical / quality', ['Dokumen','ID / Owner','Revisi','Effective date','Halaman','Checksum'], documents.map(item=>`<tr>
      <td><a href="/documents/${encodeURIComponent(item.filename)}" target="_blank" rel="noopener">${escape(item.filename)}</a></td>
      <td>${escape(item.document_id)}<small>${escape(item.owner)}</small></td><td>${escape(item.revision)}</td><td>${escape(item.effective_date || 'Belum dipetakan')}</td><td>${item.page_count}</td>
      <td>${badge(item.checksum_valid ? 'MATCH' : 'MISMATCH')}</td></tr>`))}`;
  const upload = document.querySelector('#upload-document');
  if (upload) upload.onsubmit = event=>{
    event.preventDefault();
    perform(async()=>{
      const values = new FormData(upload);
      const file = values.get('file');
      if (!file.size || file.size > 2 * 1024 * 1024) throw new Error('Pilih PDF berukuran maksimal 2 MB.');
      await withProgress(document.querySelector('#upload-progress'), async()=>{
        const encoded = await new Promise((resolve,reject)=>{
          const reader = new FileReader();
          reader.onload = ()=>resolve(String(reader.result).split(',')[1]);
          reader.onerror = ()=>reject(new Error('File tidak dapat dibaca. Pilih ulang PDF.'));
          reader.readAsDataURL(file);
        });
        const result = await api('/api/documents', {candidate_id:values.get('candidate_id'), document_id:values.get('document_id'), revision:values.get('revision'), filename:file.name, content_base64:encoded});
        location.hash = '#documents/' + result.revision_id;
        notify(result.error ? 'PDF tersimpan tetapi belum terbaca: ' + result.error : 'PDF tersimpan. Review teks sebelum ekstraksi OpenAI.');
      });
    });
  };
  if (!item) return;
  const endpoint = '/api/document-revisions/' + encodeURIComponent(item.revision_id);
  for (const action of ['extract','review','activate']) {
    const form = document.querySelector('#document-' + action);
    if (!form) continue;
    form.onsubmit = event=>{
      event.preventDefault();
      if (!form.reportValidity()) return;
      perform(async()=>{
        const progress = form.querySelector('[role="status"]');
        if (progress) progress.hidden = false;
        const body = action === 'extract' ? {consent_openai:true} : action === 'activate' ? {expected_active_revision_id:item.active_revision_id, confirm_invalidation:true} : {
          extraction_hash:item.extraction_hash, accepted_rows:[...new FormData(form).getAll('row')].map(Number), confirm_scope:true,
        };
        try { await api(endpoint + '/' + action, body); }
        catch(error) { if (progress) progress.hidden = true; throw error; }
        await showDocuments(revisionId);
        notify(action === 'activate' ? 'Revisi aktif. Approval lama langsung diblokir; buka kasus dan jalankan investigasi ulang.' : action === 'review' ? (item.active_revision_id === item.revision_id ? 'Review tersimpan untuk revisi aktif. Investigasi ulang kasus diperlukan sebelum approval atau tindakan.' : 'Review tersimpan. Aktifkan revisi ini lalu investigasi ulang kasus.') : 'Usulan ekstraksi tersimpan. Periksa kutipan dan applicability sebelum menerima evidence.');
      });
    };
  }
}

function documentDetail(item, status, canEdit) {
  const isActive = item.active_revision_id === item.revision_id;
  const rows = item.extraction?.rows || [];
  return `<section class="document-detail" aria-label="Detail revisi PDF"><h2>${escape(item.document_id)} · Rev ${escape(item.revision)}</h2>
    <p>${escape(item.candidate_id)} · ${badge(item.status)} · ${isActive ? 'AKTIF' : 'Belum aktif / arsip'}<br><a href="/documents/${escape(item.revision_id)}.pdf" target="_blank" rel="noopener">Buka PDF asli</a> · <a href="#documents">Daftar dokumen</a></p>
    <p class="muted">Diunggah ${time(item.uploaded_at)} oleh ${escape(item.uploaded_by)}. SHA-256: <code>${escape(item.sha256)}</code></p>
    ${item.error ? `<p class="notice danger">${escape(item.error)}. ${item.pages.length ? 'Ekstraksi dapat dicoba kembali secara eksplisit.' : 'PDF tidak seluruhnya terbaca. Unggah revisi baru berupa PDF teks; OCR belum tersedia.'}</p>` : ''}
    <details><summary>Teks asli hasil pembacaan (${item.pages.length} halaman)</summary>${item.pages.map((text,index)=>`<h3>Halaman ${index+1}</h3><pre class="document-text">${escape(text)}</pre>`).join('')}</details>
    ${canEdit && !item.extraction && item.pages.length ? `<form id="document-extract" class="panel"><h3>Ekstraksi Evidence Specialist</h3><label class="document-check"><input type="checkbox" required> Saya mengizinkan teks PDF dikirim ke OpenAI (${escape(status.model || 'model belum dikonfigurasi')}) dan memahami kemungkinan biaya API.</label><button type="submit" ${!status.configured ? 'disabled data-disabled="true"' : ''}>Ekstrak evidence dengan OpenAI</button>${!status.configured ? '<p>OpenAI belum dikonfigurasi di backend.</p>' : ''}<p role="status" hidden>OpenAI sedang mengekstrak teks. Tunggu hasil; tidak ada retry otomatis.</p></form>` : ''}
    ${item.extraction ? `<h3>Review usulan evidence</h3><p>Periksa kandidat, revisi, nilai, konteks, dan applicability pada PDF. Kutipan yang ditemukan belum membuktikan interpretasi AI benar. Pilih hanya klaim yang memang didukung; sisanya tetap UNKNOWN.</p>
      <form id="document-review">${rows.length ? rows.map((row,index)=>`<div class="evidence-proposal"><label class="document-check"><input name="row" value="${index}" type="checkbox" ${item.reviewed_by || row.value===null || !canEdit ? 'disabled' : ''} ${item.accepted_rows.includes(index) ? 'checked' : ''}> ${escape(row.property)}: ${escape(row.value ?? 'UNKNOWN')} ${escape(row.unit || '')}</label><p>Applicability: ${escape(row.applicability)} · <a href="/documents/${escape(item.revision_id)}.pdf#page=${row.page}" target="_blank" rel="noopener">Halaman ${row.page}</a></p><blockquote>${escape(row.quote)}</blockquote></div>`).join('') : '<p>Tidak ada klaim yang didukung. Evidence teknis akan tetap UNKNOWN.</p>'}
      ${!item.reviewed_by && canEdit ? '<label class="document-check"><input type="checkbox" required> Saya telah memeriksa identitas kandidat/revisi dan konteks tiap klaim yang dipilih. Ini bukan persetujuan produksi.</label><button type="submit">Simpan review evidence</button>' : `<p>Reviewer: ${escape(item.reviewed_by || 'Belum direview')}. Review tersimpan tidak dapat diubah; koreksi memerlukan revisi baru.</p>`}</form>
      <p class="muted">Model ${escape(item.extraction.model)} · ${escape(item.extraction.usage?.input_tokens ?? '—')} input / ${escape(item.extraction.usage?.output_tokens ?? '—')} output tokens. Hasil disimpan; membuka ulang tidak memanggil API.</p>` : ''}
    ${canEdit && !isActive ? `<form id="document-activate" class="panel"><h3>Aktifkan sebagai sumber terkini</h3><p class="notice">Aktivasi menggantikan revisi aktif untuk Document ID ini dan menghentikan prepared technical evidence kandidat. Jika ekstraksi belum direview atau gagal, evidence tersebut menjadi UNKNOWN. Approval lama langsung diblokir, bahkan sebelum investigasi ulang.</p><label class="document-check"><input type="checkbox" required> Saya menetapkan dokumen ini sebagai sumber terkini dan memahami perlunya review kasus baru.</label><button type="submit">Aktifkan revisi dan batalkan freshness lama</button></form>` : ''}
    <p><a href="#cases/CASE-001/evidence">Lanjut ke kasus untuk investigasi ulang dan perbandingan deterministik</a></p></section>`;
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
  content.innerHTML = `<section class="object-header"><div class="object-title"><a class="breadcrumb" href="#cases"><span aria-hidden="true">←</span> Recovery cases</a>
      <div class="object-title-row"><div><span class="eyebrow">Material recovery case</span><h1>${escape(caseId)} <span>· ${escape(current.exposure.material_id)}</span></h1></div>${badge(current.status)}</div>
      <p>Versi ${current.case_version} · diperbarui ${time(view.case.updated_at)}</p></div>
    <div class="object-actions"><span class="version-chip">Case version ${current.case_version}</span><button id="investigate">Investigasi ulang</button></div></section>
    ${!view.sources_current ? '<div class="context-banner danger"><strong>Sumber berubah</strong><span>Investigasi ulang diperlukan sebelum approval atau tindakan berikutnya.</span></div>' : ''}
    <div class="release-banner"><span class="release-icon" aria-hidden="true">!</span><div><span>Production release</span><strong>Terblokir</strong><small>Qualification approval tidak mengizinkan material dipakai di produksi.</small></div><a href="#cases/${encodeURIComponent(caseId)}/approvals">Lihat authorization</a></div>
    <nav class="tabs case-tabs" aria-label="Bagian kasus">${tabs.map(([key,label])=>`<a href="#cases/${encodeURIComponent(caseId)}/${key}" ${key===tab ? 'aria-current="page"' : ''}>${label}</a>`).join('')}</nav>
    <section id="case-tab">${tab==='workflow' ? AgentWorkflow.render(view,llmStatus) : ({summary:summaryTab, evidence:evidenceTab, scenarios:scenariosTab, approvals:approvalsTab}[tab])()}</section>
    <details><summary>Riwayat versi dan aktivitas investigasi</summary>${audit()}</details>`;
  document.querySelector('#investigate').onclick = ()=>perform(async()=>{
    const result = await api(caseURL() + '/investigate', snapshot());
    await route();
    notify(result.version_changed ? 'Investigasi selesai. Versi baru dibuat; approval sebelumnya perlu direview ulang.' : 'Investigasi selesai. Tidak ada perubahan decision state; versi tetap sama.');
  });
  const delayForm = document.querySelector('#inject-delay');
  if (delayForm) delayForm.addEventListener('submit', event=>{
    event.preventDefault();
    const values = new FormData(delayForm);
    perform(async()=>{
      const result = await api(caseURL() + '/delivery-delay', {
        ...snapshot(), po_id:values.get('po_id'), expected_delivery:values.get('expected_delivery'),
      });
      await route();
      notify(`Delay ${result.po_id} diterapkan. Exposure kini ${result.exposed_quantity} EA / ${result.exposed_order_count} orders.`);
    });
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
  const resequencingApprovalForm = document.querySelector('#approve-resequencing');
  if (resequencingApprovalForm) resequencingApprovalForm.addEventListener('submit', event=>{
    event.preventDefault();
    const target = view.resequencing_targets[Number(new FormData(event.target).get('target'))];
    perform(async()=>{
      await api(caseURL() + '/resequencing-approvals', {...snapshot(), scenario_id:target.scenario_id});
      await route(); notify('Approval Planner tersimpan untuk skenario resequencing yang direview.');
    });
  });
  document.querySelectorAll('[data-execute-qualification]').forEach(button=>button.onclick = ()=>perform(async()=>{
    const result = await api(caseURL() + '/qualification-tasks', {...snapshot(), approval_id:button.dataset.execute});
    await route(); notify(`Mock QMS task ${result.task.qms_task_id} berhasil dibuat. Production release tetap blocked.`);
  }));
  document.querySelectorAll('[data-execute-resequencing]').forEach(button=>button.onclick = ()=>perform(async()=>{
    const result = await api(caseURL() + '/resequencing-actions', {...snapshot(), approval_id:button.dataset.executeResequencing});
    await route(); notify(`Authorization ${result.authorization.authorization_id} dibuat. Production release tetap blocked.`);
  }));
}

function summaryTab() {
  const c = view.current;
  const exposure = c.exposure;
  const options = c.recovery_options;
  const deliveries = view.delivery_inputs || [];
  const preferred = deliveries.find(item=>item.po_id==='PO-ORIGINAL-001') || deliveries[0];
  const suggested = preferred ? new Date(Date.parse(preferred.expected_delivery + 'T00:00:00Z') + 7*86400000).toISOString().slice(0,10) : '';
  return `${preferred ? `<section class="demo-control"><div><span class="eyebrow">Interactive demo input</span><h2>Inject delayed delivery</h2><p>Ubah tanggal receipt sintetis lalu sistem langsung menghitung ulang exposure, ranking, dan case version.</p></div>
      <form id="inject-delay"><div><label for="delay-po">Purchase order</label><select id="delay-po" name="po_id">${deliveries.map(item=>`<option value="${escape(item.po_id)}" ${item.po_id===preferred.po_id?'selected':''}>${escape(item.po_id)} · ${escape(item.expected_delivery)}${item.injected?' · injected':''}</option>`).join('')}</select></div>
      <div><label for="delay-date">Delivery baru</label><input id="delay-date" name="expected_delivery" type="date" value="${escape(suggested)}" required></div><button type="submit">Inject delay &amp; hitung ulang</button></form></section>` : ''}
    <section class="metric-grid case-metrics" aria-label="Ringkasan kasus">
    <article class="metric"><span>Stok usable</span><strong>${exposure.current_usable_stock} <em>EA</em></strong><small>current available stock</small></article>
    <article class="metric critical"><span>Shortage pertama</span><strong>${escape(date(exposure.shortage_date))}</strong><small>tanggal risiko terdekat</small></article>
    <article class="metric critical"><span>Produksi exposed</span><strong>${c.simulation.baseline_exposed_quantity} <em>EA</em></strong><small>${c.simulation.baseline_exposed_order_count} production orders</small></article>
    <article class="metric"><span>Approved coverage</span><strong>${options.approved_covered_quantity} / ${options.required_quantity} <em>EA</em></strong><small>${options.approved_recovery_sufficient ? 'Coverage mencukupi' : 'Coverage belum mencukupi'}</small></article></section>
    <section class="decision-brief"><div><span class="eyebrow">Decision brief</span><h2>${options.approved_recovery_sufficient ? 'Approved recovery mencukupi' : 'Approved recovery belum mencukupi'}</h2><p>${options.approved_recovery_sufficient ? `Jalur approved melindungi kebutuhan ${options.required_quantity} EA. Verifikasi authorization sebelum tindakan operasional.` : `Belum ada jalur approved yang melindungi ${options.required_quantity} EA. Kandidat alternatif harus melewati evidence review dan qualification gate sebelum dapat dipertimbangkan.`}</p></div>
      <div class="decision-next"><span>Langkah berikutnya</span><a href="#cases/${encodeURIComponent(view.case.case_id)}/evidence">Review evidence kandidat <span aria-hidden="true">→</span></a><a href="#cases/${encodeURIComponent(view.case.case_id)}/scenarios">Bandingkan recovery scenario <span aria-hidden="true">→</span></a></div></section>
    <div class="section-heading"><div><span class="eyebrow">Approved-first search</span><h2>Approved recovery diperiksa terlebih dahulu</h2></div><p>As-of ${time(exposure.as_of)}</p></div>
    ${table('Urutan pencarian recovery', ['Kategori','Opsi dievaluasi','Hasil'], options.search_trace.map(step=>`<tr><td>${escape(step.category)}</td><td>${escape(step.evaluated_option_ids.join(', ') || 'Tidak ada')}</td><td>${badge(step.outcome)}</td></tr>`))}
    <div class="section-heading"><div><span class="eyebrow">Unqualified supply</span><h2>Kandidat alternatif</h2></div></div>
    ${table('Availability bukan readiness', ['Kandidat','ETA','Tiba sebelum shortage?','Quantity','Hasil review'], options.unqualified_candidates.map(option=>{
      const comparison = c.candidate_comparisons.find(item=>item.candidate_id===option.candidate_id);
      return `<tr><td>${escape(option.candidate_id)}</td><td>${escape(option.ready_date)}</td><td>${option.arrives_by_need ? 'Ya' : 'Tidak'}</td><td>${option.available_quantity} EA</td><td>${badge(comparison?.decision || 'UNKNOWN')}</td></tr>`;
    }))}
    <div class="section-heading"><div><span class="eyebrow">Baseline exposure</span><h2>Production orders terdampak</h2></div></div>
    ${table('Dampak baseline sebelum recovery', ['Order','Assembly','Scheduled','Required','Unserved'], exposure.affected_orders.map(order=>`<tr><td>${escape(order.order_id)}</td><td>${escape(order.product_id)}</td><td>${escape(order.scheduled_date)}</td><td>${order.required_material_quantity} EA</td><td>${order.unserved_quantity} EA</td></tr>`))}`;
}

function sourceLink(source) {
  const known = documents.some(item=>item.filename===source.source_document);
  const label = `${escape(source.source_document)} · Rev ${escape(source.source_revision)} · p.${escape(source.source_page)}`;
  const page = /^\d+$/.test(source.source_page) ? '#page=' + source.source_page : '';
  return `<span class="source">${known ? `<a href="/documents/${encodeURIComponent(source.source_document)}${page}" target="_blank" rel="noopener">${label}</a>` : label}<small>${escape(source.source_location)} · ${escape(source.applicability)}</small></span>`;
}

function evidenceTab() {
  return `<section class="tab-heading"><div><span class="eyebrow">Deterministic comparison</span><h2>Requirement-level evidence</h2><p>Setiap status berasal dari comparison backend. Bukti yang belum cukup tetap ditandai belum diketahui.</p></div></section><div class="candidate-stack">${view.current.candidate_comparisons.map(candidate=>`
    <section class="candidate-card"><header><div><span class="eyebrow">Candidate</span><h3>${escape(candidate.candidate_id)}</h3></div>${badge(candidate.decision)}</header>
    ${table('Evidence ' + candidate.candidate_id, ['Requirement','Dibutuhkan','Observed','Status / alasan','Sumber'], candidate.rows.map(row=>`<tr>
      <td>${escape(row.requirement_name)}<small>${escape(row.requirement_id)}</small></td><td>${escape(row.required_operator)} ${escape(row.required_value)} ${escape(row.required_unit || '')}</td>
      <td>${row.observed_value===null ? 'Belum diketahui' : escape(row.observed_value)} ${escape(row.observed_unit || '')}</td><td>${badge(row.status)}<small>${escape(row.reason)}</small></td>
      <td>${row.evidence.length ? row.evidence.map(sourceLink).join('') : 'Tidak ada applicable evidence'}</td></tr>`))}</section>`).join('')}</div>`;
}

function scenariosTab() {
  const c = view.current;
  const ranked = [...c.simulation.scenarios].sort((a,b)=>a.rank-b.rank);
  const groups = [
    ['FEASIBLE','Feasible options','Dapat melindungi semua order pada kondisi yang dihitung.'],
    ['CONDITIONAL','Conditional options','Masih menyisakan exposure atau bergantung pada kondisi yang belum selesai.'],
    ['NOT_ACTIONABLE','Not actionable','Belum layak dijalankan dari snapshot ini.'],
  ];
  const card = item=>`<article class="scenario-card ${item.rank===1 ? 'featured' : ''}"><header><span>Rank #${item.rank}</span>${badge(item.state)}</header><h3>${escape(item.name)}</h3>
      <p class="rank-reason"><strong>Alasan ranking:</strong> ${escape(item.rank_reason)}</p>
      <dl><div><dt>Siap</dt><dd>${time(item.ready_at)}</dd></div><div><dt>Protected</dt><dd>${item.protected_quantity} EA</dd></div><div><dt>Sisa exposed</dt><dd>${item.remaining_exposed_quantity} EA · ${item.remaining_exposed_order_count} orders</dd></div><div><dt>Biaya tambahan</dt><dd>${(item.incremental_cost_cents / 100).toLocaleString('id-ID')}</dd></div></dl>
      <p>${item.ready_by_shortage===null ? 'Timing belum terselesaikan.' : item.ready_by_shortage ? 'Siap paling lambat saat shortage.' : 'Siap setelah shortage.'}</p>${item.unresolved_conditions.length ? `<small>${escape(item.unresolved_conditions.join('; '))}</small>` : ''}</article>`;
  return `<section class="tab-heading"><div><span class="eyebrow">Recovery simulation</span><h2>Perbandingan recovery</h2><p>Bandingkan coverage, timeline, dan biaya. Feasibility tidak menggantikan authorization.</p></div><span class="data-context">Shortage · ${time(c.simulation.shortage_at)}</span></section>
    ${groups.map(([key,title,description])=>{
      const items = ranked.filter(item=>item.ranking_group===key);
      return items.length ? `<section class="scenario-group"><div class="section-heading"><div><span class="eyebrow">${escape(key.replace('_',' '))}</span><h3>${title}</h3></div><p>${description}</p></div><div class="scenario-grid">${items.map(card).join('')}</div></section>` : '';
    }).join('')}
    <div class="section-heading"><div><span class="eyebrow">Dependency schedule</span><h2>Qualification timeline</h2></div><p>Jadwal qualification, bukan hasil test yang sudah lulus.</p></div>
    ${c.qualification_graphs.map(graph=>`<h3>${escape(graph.candidate_id)} · selesai terjadwal ${time(graph.qualification_complete)}</h3>
      ${table('Task dependencies ' + graph.candidate_id, ['Task','Mulai','Selesai','Durasi kerja','Dependency / resource'], graph.schedules.map(task=>`<tr><td>${escape(task.name)}<small>${badge(task.status)}</small></td><td>${time(task.start_time)}</td><td>${time(task.end_time)}</td><td>${escape(task.duration_hours ?? 'Unknown')} jam</td><td>${escape(task.predecessor_ids.join(', ') || 'Tidak ada')}<small>${escape(task.required_resource || 'Tanpa resource kalender')}</small></td></tr>`))}`).join('') || '<p>Qualification plan belum tersedia.</p>'}`;
}

function approvalsTab() {
  const targets = view.qualification_targets;
  const mayApprove = view.can_approve && view.sources_current && targets.length;
  const resequencingTargets = view.resequencing_targets || [];
  const mayApproveResequencing = view.can_authorize_resequencing && view.sources_current && resequencingTargets.length;
  const qualificationApprovals = view.approvals.filter(item=>item.scope.kind==='QUALIFICATION');
  const resequencingApprovals = view.approvals.filter(item=>item.scope.kind==='RESEQUENCING');
  return `<section class="tab-heading"><div><span class="eyebrow">Human control point</span><h2>Review dan authorization</h2><p>Setiap approval terikat role, case version, case hash, sumber, dan tindakan spesifik. Production release tetap terblokir.</p></div></section>
    ${mayApprove ? `<form id="approve" class="panel approval-panel"><div><span class="eyebrow">Approval scope</span><h3>Authorize qualification task</h3><label for="target">Qualification target</label><select id="target" name="target">${targets.map((item,index)=>`<option value="${index}">${escape(item.candidate_id)} · ${escape(item.task_name)} · ${escape(item.requirement_id)}</option>`).join('')}</select></div><div class="approval-summary"><span>Case version</span><strong>${view.current.case_version}</strong><span>Validity</span><strong>8 jam</strong></div><button type="submit">Approve qualification task</button></form>` : `<p class="notice">${!view.can_approve ? 'Role Anda tidak dapat menyetujui qualification task. Login sebagai Engineering Reviewer atau Quality Engineer.' : !view.sources_current ? 'Sumber berubah. Investigasi ulang sebelum approval.' : 'Tidak ada qualification target yang berlaku.'}</p>`}
    ${mayApproveResequencing ? `<form id="approve-resequencing" class="panel approval-panel"><div><span class="eyebrow">Planner control</span><h3>Authorize production resequencing</h3><label for="resequencing-target">Skenario</label><select id="resequencing-target" name="target">${resequencingTargets.map((item,index)=>`<option value="${index}">Rank #${item.rank} · ${escape(item.scenario_name)} · ${escape(item.state)}</option>`).join('')}</select><small>${escape(resequencingTargets[0].rank_reason)}</small></div><div class="approval-summary"><span>Case version</span><strong>${view.current.case_version}</strong><span>Validity</span><strong>8 jam</strong></div><button type="submit">Approve resequencing</button></form>` : `<p class="notice">${!view.can_authorize_resequencing ? 'Production resequencing hanya dapat disetujui oleh Production Planner.' : !view.sources_current ? 'Sumber berubah. Investigasi ulang sebelum approval.' : 'Tidak ada skenario resequencing yang actionable.'}</p>`}
    <div class="section-heading"><div><span class="eyebrow">Authorization trail</span><h3>Approval records</h3></div></div>
    ${view.approvals.length ? table('Authorization bound to case version', ['Approval / target','Reviewer','Versi','Berlaku sampai','Pemeriksaan','Tindakan'], view.approvals.map(item=>`<tr>
      <td>${escape(item.approval_id)}<small>${item.scope.kind==='QUALIFICATION' ? `${escape(item.scope.candidate_id)} · ${escape(item.scope.requirement_id)}` : escape(item.scope.scenario_name)}</small></td><td>${escape(item.approver_id)}<small>${escape(item.approver_role)}</small></td>
      <td>${item.case_version}</td><td>${time(item.expires_at)}</td><td>${badge(item.validation.status)}<small>${escape(item.validation.reasons.join(', '))}</small></td>
      <td>${item.scope.kind==='QUALIFICATION' ? `<button class="secondary" data-execute-qualification data-execute="${escape(item.approval_id)}" ${item.validation.status!=='AUTHORIZED' ? 'disabled data-disabled="true"' : ''}>Create mock QMS task</button>` : `<button class="secondary" data-execute-resequencing="${escape(item.approval_id)}" ${item.validation.status!=='AUTHORIZED' ? 'disabled data-disabled="true"' : ''}>Create mock authorization</button>`}</td></tr>`)) : '<p>Belum ada approval. Review bukti dan skenario sebelum memberi authorization.</p>'}
    <div class="section-heading"><div><span class="eyebrow">Execution receipts</span><h3>Qualification tasks &amp; receipts</h3></div></div>
    ${view.tasks.length ? table('Mock QMS tasks tersimpan', ['QMS ID','Kandidat / requirement','Task','Dibuat','Status'], view.tasks.map(task=>`<tr><td>${escape(task.qms_task_id)}</td><td>${escape(task.candidate_id)}<small>${escape(task.requirement_id)}</small></td><td>${escape(task.task_name)}</td><td>${time(task.created_at)}</td><td>${badge(task.status)}</td></tr>`)) : '<p>Belum ada QMS task yang dibuat.</p>'}
    ${view.case.actions.map(action=>`<details><summary>Receipt ${escape(action.external_reference)} · ${escape(action.action_type)}</summary><dl><dt>Action</dt><dd>${escape(action.action_id)}</dd><dt>Reviewed version</dt><dd>${action.case_version}</dd><dt>Case hash</dt><dd><code>${escape(action.case_hash)}</code></dd><dt>Idempotency key</dt><dd><code>${escape(action.idempotency_key)}</code></dd></dl></details>`).join('')}`;
}

function audit() {
  return table('Immutable case versions', ['Version','Dibuat','Reason','Hash'], view.case.versions.map(version=>`<tr><td>${version.case_version}</td><td>${time(version.created_at)}</td><td>${escape(version.change_reason)}</td><td><code>${escape(version.case_hash)}</code></td></tr>`)) +
    table('Aktivitas investigasi terakhir', ['Urutan','Tool','Target','Hasil'], view.tool_trace.map(step=>`<tr><td>${step.sequence}</td><td>${escape(step.tool)}</td><td>${escape(step.target)}</td><td>${escape(step.outcome)}</td></tr>`));
}

window.addEventListener('hashchange', ()=>{
  if (busy) routePending = true;
  else perform(route);
});
document.addEventListener('click', event=>{
  const toggle = event.target.closest('[data-popover]');
  if (toggle) {
    const panel = document.getElementById(toggle.dataset.popover);
    const open = panel.hidden;
    closePopovers(panel.id);
    panel.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    return;
  }
  if (!event.target.closest('.popover') || event.target.closest('.popover a')) closePopovers();
});
document.addEventListener('keydown', event=>{
  if (event.key !== 'Escape') return;
  const open = document.querySelector('.popover:not([hidden])');
  if (!open) return;
  closePopovers();
  document.querySelector(`[data-popover="${open.id}"]`)?.focus();
});
perform(async()=>{
  try { session = await api('/api/session'); }
  catch(error) { if(error.status!==401) throw error; }
  await route();
});
