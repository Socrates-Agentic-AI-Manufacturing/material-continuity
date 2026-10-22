/* Inspectable workflow, not a workflow editor. All business facts come from the API.
   Local case map and recorded OpenAI calls are deliberately different views. */
(() => {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const json = value => esc(JSON.stringify(value, null, 2));
  const nodeWidth = 224, nodeHeight = 132;
  const descriptions = {
    getExposure: ['Hitung dampak produksi', 'Code', 'Stok, shortage, dan order terdampak dihitung oleh backend, bukan perkiraan AI.', 'exposure'],
    findRecoveryOptions: ['Periksa opsi approved', 'Code', 'Opsi yang sudah disetujui diperiksa lebih dahulu sebelum kandidat baru.', 'discovery'],
    getCandidateEvidence: ['Review bukti kandidat', 'Evidence', 'Baca comparison yang sudah dihitung backend, termasuk gap dan sumber/halaman. Bukan pembacaan PDF langsung.', 'evidence'],
    getQualificationDependencies: ['Jadwalkan kualifikasi', 'Code', 'Backend menghitung dependency dan kalender pengujian. Jadwal bukan hasil test yang sudah lulus.', 'qualification'],
    simulateRecovery: ['Bandingkan recovery', 'Code', 'Bandingkan substitusi, expedite, dan resequencing berdasarkan hasil deterministik. Feasible bukan authorized.', 'simulation'],
    finishReview: ['Susun advisory AI', 'OpenAI', 'Ringkasan model membantu reviewer memahami kasus; tidak mengubah bukti, approval, atau izin produksi.', 'advisory'],
  };
  function toolOutput(tool, target, facts, review) {
    if (tool === 'getExposure') return facts.exposure;
    if (tool === 'findRecoveryOptions') return facts.recovery_options;
    if (tool === 'getCandidateEvidence') return facts.candidate_comparisons.find(item => item.candidate_id === target) || null;
    if (tool === 'getQualificationDependencies') return facts.qualification_graphs.find(item => item.candidate_id === target) || null;
    if (tool === 'simulateRecovery') return facts.simulation;
    if (tool === 'finishReview') return review;
    return null;
  }
  function layout(nodes) {
    return nodes.map((node, index) => {
      const row = Math.floor(index / 3), column = row % 2 ? 2 - index % 3 : index % 3;
      return {...node, x: 34 + column * 266, y: 40 + row * 202};
    });
  }
  function build(view, mode = 'local') {
    const saved = view.latest_ai_review;
    const facts = mode === 'ai' && saved ? saved.facts : view.current;
    const context = {case_id: view.case.case_id, case_version: mode === 'ai' && saved ? saved.case_version : view.current.case_version, case_hash: mode === 'ai' && saved ? saved.case_hash : view.current.case_hash};
    if (mode === 'ai') {
      if (!saved) return [];
      return layout(saved.tool_trace.map(step => {
        const meta = descriptions[step.tool] || [step.tool, 'Tool', 'Jejak yang direkam backend.', 'code'];
        return {id: 'ai-' + step.sequence, title: meta[0], owner: meta[1], explanation: meta[2], kind: meta[3],
          subtitle: step.target, status: step.tool === 'finishReview' ? 'ADVISORY' : 'READ',
          context: {...context, tool: step.tool, target: step.target}, output: toolOutput(step.tool, step.target, facts, saved.review)};
      }));
    }
    const trace = view.tool_trace;
    const ran = tool => trace.some(step => step.tool === tool);
    const core = (tool, extra = {}) => {
      const meta = descriptions[tool];
      return {id: tool, title: meta[0], owner: meta[1], explanation: meta[2], kind: meta[3],
        subtitle: tool, status: ran(tool) ? 'RECORDED' : 'NOT_RUN', context: {...context, tool},
        output: toolOutput(tool, '', facts), ...extra};
    };
    return layout([
      {id:'trigger', title:'Gangguan material', owner:'Event', kind:'trigger', subtitle:facts.trigger.trigger_type,
        status:'RECORDED', explanation:'Pemicu kasus ini berasal dari fixture enterprise sintetis; belum ada event SAP/AWS langsung.', context, output:facts.trigger},
      core('getExposure'), core('findRecoveryOptions'),
      {id:'evidence', title:'Evidence Specialist', owner:'Lokal / evidence', kind:'evidence', subtitle:facts.candidate_comparisons.length + ' kandidat direview',
        status:ran('EvidenceSpecialist') ? 'RECORDED' : 'NOT_RUN', explanation:'Workflow lokal memetakan prepared evidence atau hasil PDF aktif yang telah direview ke requirement. Ekstraksi OpenAI terpisah di Documents & Data. Hard mismatch ditolak; bukti hilang tetap UNKNOWN.', context,
        output:{candidate_comparisons:facts.candidate_comparisons, trace:trace.filter(step=>step.tool==='EvidenceSpecialist')}},
      core('getQualificationDependencies', {output:facts.qualification_graphs}), core('simulateRecovery'),
      {id:'case', title:'Simpan versi kasus', owner:'Code', kind:'case', subtitle:'Versi ' + facts.case_version,
        status:'VERSIONED', explanation:'Case hash mengikat bukti dan keputusan yang direview. Perubahan sumber dapat membuat approval lama tidak berlaku.', context,
        output:{case_version:facts.case_version, case_hash:facts.case_hash, source_versions:facts.source_versions}},
      {id:'human', title:'Review & approval', owner:'Manusia', kind:'human', subtitle:view.approvals.length + ' approval records',
        status:'HUMAN_GATE', explanation:'Hanya reviewer dengan role yang sesuai dapat mengizinkan qualification task. Status authorization di bawah berasal dari backend, bukan dari AI.', context,
        output:view.approvals, link:'approvals', linkText:'Buka Approval & Actions'},
      {id:'action', title:'Qualification task', owner:'Mock QMS', kind:'action', subtitle:view.tasks.length + ' task dalam riwayat',
        status:view.tasks.length ? 'RECEIPT_RECORDED' : 'NOT_EXECUTED', explanation:'Riwayat task dapat mencakup versi lama; versi asli ada pada receipt. Adapter hanya menulis setelah pemeriksaan izin, freshness dan duplikasi. Task bukan release material.', context,
        output:{tasks:view.tasks, receipts:view.case.actions, production_release_authorized:false}, link:'approvals', linkText:'Lihat task & receipt'},
    ]);
  }
  function icon(kind) {
    const paths = {
      trigger:'M13 2 4 13h7l-1 9 10-13h-7z',
      exposure:'M4 18V6m5 12v-7m5 7V3m5 15v-9M3 21h18',
      discovery:'M4 4h6v6H4zM14 14h6v6h-6zM14 4h6v6h-6zM7 10v7h7M10 7h4',
      evidence:'M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h5',
      qualification:'M4 5h16v16H4zM8 2v6M16 2v6M4 10h16M8 14h3M13 17h3',
      simulation:'M3 18h18M6 14V9m6 5V4m6 10V7M4 6l4-3',
      advisory:'M5 6h14v12H5zM9 6V3m6 3V3M2 10h3m14 0h3M9 11v2m6-2v2M9 16h6',
      case:'M4 6h16v15H4zM7 3h10v3M8 11h8M8 15h6',
      human:'M8 7a4 4 0 1 0 8 0a4 4 0 1 0-8 0M4 21v-3a5 5 0 0 1 5-5h6a5 5 0 0 1 5 5v3',
      action:'M5 3h14v18H5zM8 8l2 2 5-5M8 14h8M8 18h5',
    };
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[kind] || paths.case}"/></svg>`;
  }
  function nodeHTML(node, index) {
    return `<button type="button" class="flow-node flow-${esc(node.kind)}" data-flow-node="${index}" aria-pressed="false">
      <span class="flow-node-head">${icon(node.kind)}<span>${esc(node.owner)}</span><span class="flow-sequence">${index+1}</span></span>
      <strong>${esc(node.title)}</strong><span class="flow-node-target">${esc(node.subtitle)}</span><span class="flow-state">${esc(node.status)}</span></button>`;
  }
  function render(view, status) {
    const saved = view.latest_ai_review;
    const enabled = status.configured && view.sources_current;
    return `<section class="workflow" aria-labelledby="workflow-title">
      <div class="workflow-intro"><div><h2 id="workflow-title">Agent Workflow</h2><p>Ikuti bagaimana bukti menjadi keputusan. Klik node untuk membuka konteks dan hasil backend.</p></div>
        <span class="flow-provider">${status.configured ? 'OpenAI tersedia · ' + esc(status.model) : 'OpenAI belum aktif'}</span></div>
      <form id="ai-review-form" class="ai-review-form"><div><label class="cost-consent"><input type="checkbox" id="ai-cost-consent" required ${!enabled ? 'disabled' : ''}> Saya memahami review ini mengirim data kasus sintetis ke OpenAI dan memakai kredit API.</label>
        <small>${!view.sources_current ? 'Sumber berubah: jalankan investigasi ulang dahulu.' : !status.configured ? 'Aktifkan provider, key dan model di backend lalu restart server.' : 'Maksimal 12 panggilan / 90 detik. Tidak ada panggilan otomatis saat membuka halaman.'}</small></div>
        <button type="submit" id="ai-review" ${!enabled ? 'disabled data-disabled="true"' : ''}>Review dengan AI</button></form>
      <p id="ai-review-progress" role="status" aria-live="polite" hidden></p>
      <div id="ai-review-error" class="notice danger" role="alert" hidden></div>
      ${saved && !saved.is_current ? '<p class="notice danger">Review AI tersimpan berasal dari sumber atau versi lama. Ini hanya arsip, bukan rekomendasi untuk keadaan saat ini.</p>' : ''}
      <div class="flow-toolbar"><div class="flow-mode"><label for="flow-source">Sumber alur</label><select id="flow-source"><option value="local">Alur kasus lokal</option><option value="ai" ${!saved ? 'disabled' : ''}>Jejak review OpenAI${saved ? ' · v' + saved.case_version : ' · belum dijalankan'}</option></select></div>
        <div class="actions"><button type="button" class="secondary" id="flow-view">Tampilan daftar</button><button type="button" class="secondary" id="flow-fit">Pas ke layar</button>
        <button type="button" class="secondary" id="flow-minus" aria-label="Perkecil canvas">−</button><output id="flow-zoom" aria-label="Zoom canvas">100%</output><button type="button" class="secondary" id="flow-plus" aria-label="Perbesar canvas">+</button></div></div>
      <p class="flow-caption" id="flow-caption"></p>
      <div class="flow-workspace"><div class="flow-board"><div class="flow-viewport" id="flow-viewport" tabindex="0" role="region" aria-label="Canvas workflow interaktif" aria-describedby="flow-help">
        <div class="flow-plane" id="flow-plane"></div></div><div id="flow-list" class="flow-list" hidden></div>
        <div class="flow-replay"><button type="button" class="secondary" id="flow-prev" aria-label="Langkah sebelumnya">Sebelumnya</button><button type="button" id="flow-play">Putar replay</button><button type="button" class="secondary" id="flow-next" aria-label="Langkah berikutnya">Berikutnya</button><span id="flow-step" role="status" aria-live="polite"></span></div>
        <p id="flow-help">Geser area kosong untuk pan. Fokus canvas lalu gunakan tombol panah; Tab untuk memilih node. Replay hanya menelusuri catatan, tidak menjalankan ulang tools atau memakai kredit.</p></div>
        <aside class="flow-inspector" id="flow-inspector" aria-label="Detail node terpilih"></aside></div>
      <div class="flow-legend"><span>Code: hitung & validasi</span><span>OpenAI: advisory baca-saja</span><span>Manusia: otorisasi</span><span>QMS: task simulasi</span></div>
      <div id="ai-review-result">${saved ? reviewHTML(saved) : '<p>Belum ada review OpenAI tersimpan. Alur lokal tetap bisa dieksplorasi tanpa biaya API.</p>'}</div>
    </section>`;
  }
  function reviewHTML(saved) {
    const names = {REVIEW_EVIDENCE_GAPS:'Review gap bukti', REVIEW_QUALIFICATION_PLAN:'Review rencana kualifikasi', REVIEW_RECOVERY_SCENARIOS:'Bandingkan skenario recovery', REQUEST_HUMAN_REVIEW:'Minta review manusia'};
    return `<section class="ai-advisory"><h3>Advisory OpenAI${!saved.is_current ? ' · arsip lama' : ''}</h3><p class="advisory-text">${esc(saved.review.summary)}</p>
      <p><strong>Bukan approval, bukti baru, atau izin produksi.</strong> Angka dan status resmi tetap ada di Evidence Review dan Recovery Scenarios.</p>
      <ul>${saved.review.next_steps.map(step=>`<li>${esc(names[step] || step)}</li>`).join('')}</ul>
      <small>${esc(saved.model)} · Versi ${saved.case_version} · ${saved.tool_trace.length} tool calls · ${saved.usage.input_tokens.toLocaleString('id-ID')} input / ${saved.usage.output_tokens.toLocaleString('id-ID')} output tokens · ${esc(saved.created_at)}</small></section>`;
  }
  function keepListNodeVisible(list, button) {
    const listRect=list.getBoundingClientRect(), nodeRect=button.getBoundingClientRect();
    if (nodeRect.top < listRect.top || nodeRect.bottom > listRect.bottom) {
      list.scrollTop += nodeRect.top-listRect.top-Math.max(0,(list.clientHeight-nodeRect.height)/2);
    }
  }
  function explainResult(node) {
    const value=node.output;
    if (!value) return '<p>Langkah ini tidak dijalankan pada investigasi yang direkam.</p>';
    if (node.kind==='exposure') return `<dl class="flow-result-facts"><dt>Stok usable</dt><dd>${esc(value.current_usable_stock)} EA</dd><dt>Shortage pertama</dt><dd>${esc(value.shortage_date)}</dd><dt>Order terdampak</dt><dd>${value.affected_orders.length} order</dd></dl>`;
    if (node.kind==='discovery') return `<p>Approved coverage: <strong>${esc(value.approved_covered_quantity)} / ${esc(value.required_quantity)} EA</strong>.</p><p>Approved recovery cukup: <strong>${value.approved_recovery_sufficient?'Ya':'Belum'}</strong>. Kandidat baru tetap perlu pemeriksaan bukti.</p>`;
    if (node.kind==='evidence') {
      const candidates=value.candidate_comparisons || [value];
      return candidates.map(candidate=>`<div class="flow-evidence-summary"><strong>${esc(candidate.candidate_id)}</strong><p>${esc(candidate.decision)}</p><ul>${candidate.rows.map(row=>`<li>${esc(row.requirement_name)}: <strong>${esc(row.status)}</strong></li>`).join('')}</ul></div>`).join('');
    }
    if (node.kind==='qualification') {
      const graphs=Array.isArray(value)?value:[value];
      return graphs.map(graph=>`<p><strong>${esc(graph.candidate_id)}</strong><br>Selesai terjadwal: ${esc(graph.qualification_complete || 'Belum diketahui')}<br>Ini rencana, bukan bukti test sudah selesai.</p>`).join('') || '<p>Belum ada rencana kualifikasi yang berlaku.</p>';
    }
    if (node.kind==='simulation') return value.scenarios.map(scenario=>`<div class="flow-scenario-summary"><strong>${esc(scenario.name)}</strong><p>${esc(scenario.state)} · ${esc(scenario.remaining_exposed_quantity)} EA masih exposed</p></div>`).join('');
    if (node.kind==='human') return `<p>${value.length} approval records. Validitas tetap diperiksa ulang saat tindakan dilakukan.</p>`;
    if (node.kind==='action') return `<p>${value.tasks.length} task tersimpan. <strong>Production release tetap BLOCKED.</strong></p>`;
    if (node.kind==='advisory') return `<p class="advisory-text">${esc(value.summary)}</p><p><strong>Advisory, bukan izin tindakan.</strong></p>`;
    return '<p>Detail dan sumber asli dari snapshot tersedia di bawah.</p>';
  }
  function mount(root, view, {preferAI = false} = {}) {
    let mode = preferAI && view.latest_ai_review ? 'ai' : 'local';
    let nodes = [], selected = 0, scale = 1, tx = 0, ty = 0, timer = null, drag = null;
    let listMode = window.matchMedia('(max-width: 700px)').matches;
    const el = id => root.querySelector('#' + id);
    const viewport = el('flow-viewport'), plane = el('flow-plane');
    const stop = () => { if (timer) clearInterval(timer); timer = null; el('flow-play').textContent = 'Putar replay'; };
    function transform() {
      plane.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
      el('flow-zoom').textContent = Math.round(scale * 100) + '%';
    }
    function fit() {
      if (listMode) return;
      const height = 202 * Math.ceil(nodes.length / 3) + 12;
      scale = Math.max(.35, Math.min(1, (viewport.clientWidth - 24) / 820, (viewport.clientHeight - 24) / height));
      tx = (viewport.clientWidth - 820 * scale) / 2;
      ty = Math.max(0, (viewport.clientHeight - height * scale) / 2);
      transform();
    }
    function disabled(button, value) { button.disabled = value; button.dataset.disabled = String(value); }
    function inspect(index, recenter = false) {
      selected = Math.max(0, Math.min(nodes.length - 1, index));
      const node = nodes[selected];
      if (!node) return;
      root.querySelectorAll('[data-flow-node]').forEach(button=>button.setAttribute('aria-pressed', String(Number(button.dataset.flowNode) === selected)));
      root.querySelectorAll('.flow-connection').forEach((path,i)=>path.classList.toggle('flow-connection-selected', i === selected - 1));
      el('flow-step').textContent = `Langkah ${selected+1} / ${nodes.length} · replay catatan`;
      disabled(el('flow-prev'), selected === 0); disabled(el('flow-next'), selected === nodes.length-1);
      el('flow-inspector').innerHTML = `<div class="flow-detail-title">${icon(node.kind)}<h3>${esc(node.title)}</h3></div><p class="flow-owner">${esc(node.owner)} · ${esc(node.status)}</p><p>${esc(node.explanation)}</p>
        <div class="flow-result-summary">${explainResult(node)}</div>
        <details><summary>Konteks snapshot</summary><pre tabindex="0">${json(node.context)}</pre></details><details><summary>Output lengkap${node.kind === 'advisory' ? ' (advisory)' : ' backend'}</summary><pre tabindex="0">${json(node.output)}</pre></details>
        ${node.link ? `<a href="#cases/${encodeURIComponent(view.case.case_id)}/${node.link}">${esc(node.linkText)}</a>` : ''}`;
      if (recenter && !listMode) {
        tx = viewport.clientWidth/2 - (node.x+nodeWidth/2)*scale;
        ty = viewport.clientHeight/2 - (node.y+nodeHeight/2)*scale; transform();
      } else if (recenter && listMode) {
        // Scroll the internal list only. scrollIntoView would move the whole
        // page away from the inspector/replay controls on a small screen.
        const list = el('flow-list');
        const button = list.querySelector(`[data-flow-node="${selected}"]`);
        keepListNodeVisible(list,button);
      }
    }
    function draw() {
      stop(); nodes = build(view, mode); selected = 0;
      el('flow-source').value = mode;
      el('flow-caption').textContent = mode === 'ai'
        ? 'Jejak OpenAI yang benar-benar selesai. Urutan mengikuti tool calls model; hasil memakai snapshot saat review, bukan bukti PDF baru.'
        : 'Peta tahap kasus yang dikelompokkan, bukan urutan tool call individual. Evidence mengikuti sumber aktif; approval dan QMS adalah catatan tahap terpisah dengan human gate.';
      const height = 202 * Math.ceil(nodes.length/3) + 12;
      const edges = nodes.slice(1).map((node,i) => {
        const before = nodes[i];
        const vertical = node.y !== before.y;
        const forward = node.x > before.x;
        const x1 = vertical ? before.x+nodeWidth/2 : before.x+(forward ? nodeWidth : 0);
        const y1 = before.y+(vertical ? nodeHeight : nodeHeight/2);
        const x2 = vertical ? node.x+nodeWidth/2 : node.x+(forward ? 0 : nodeWidth);
        const y2 = node.y+(vertical ? 0 : nodeHeight/2);
        const d = vertical ? `M${x1} ${y1} C${x1} ${y1+35} ${x2} ${y2-35} ${x2} ${y2}` : `M${x1} ${y1} C${x1+(forward?25:-25)} ${y1} ${x2+(forward?-25:25)} ${y2} ${x2} ${y2}`;
        return `<path class="flow-connection ${node.kind==='human' || node.kind==='action' ? 'flow-gated' : ''}" d="${d}" marker-end="url(#flow-arrow)"/>`;
      }).join('');
      plane.innerHTML = `<svg class="flow-edges" width="820" height="${height}" aria-hidden="true"><defs><marker id="flow-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 10 5 0 10z"/></marker></defs>${edges}</svg>` + nodes.map(nodeHTML).join('');
      plane.style.width='820px'; plane.style.height=height+'px';
      plane.querySelectorAll('[data-flow-node]').forEach((button,i)=>{button.style.left=nodes[i].x+'px';button.style.top=nodes[i].y+'px';});
      el('flow-list').innerHTML = nodes.map((node,i)=>`<div>${nodeHTML(node,i)}</div>`).join('');
      root.querySelectorAll('[data-flow-node]').forEach(button=>{
        button.onclick=()=>{stop();inspect(Number(button.dataset.flowNode));};
        button.onfocus=()=>{if(!listMode && document.activeElement===button) inspect(Number(button.dataset.flowNode), true);};
      });
      toggleView(); inspect(0); fit();
    }
    function toggleView() {
      viewport.hidden=listMode; el('flow-list').hidden=!listMode;
      el('flow-view').textContent=listMode ? 'Tampilan canvas' : 'Tampilan daftar';
      for (const name of ['flow-fit','flow-minus','flow-plus']) disabled(el(name),listMode);
    }
    el('flow-view').onclick=()=>{stop();listMode=!listMode;toggleView();fit();inspect(selected,true);};
    el('flow-source').onchange=event=>{mode=event.target.value;draw();};
    el('flow-fit').onclick=fit;
    function zoom(factor) {
      const old=scale; scale=Math.min(1.75, Math.max(.35,scale*factor));
      tx=viewport.clientWidth/2-(viewport.clientWidth/2-tx)*scale/old;
      ty=viewport.clientHeight/2-(viewport.clientHeight/2-ty)*scale/old;transform();
    }
    el('flow-plus').onclick=()=>zoom(1.2);el('flow-minus').onclick=()=>zoom(1/1.2);
    el('flow-prev').onclick=()=>{stop();inspect(selected-1,true);};
    el('flow-next').onclick=()=>{stop();inspect(selected+1,true);};
    el('flow-play').onclick=()=>{
      if(timer){stop();return;}
      if(selected===nodes.length-1)inspect(0,true);
      el('flow-play').textContent='Jeda replay';
      timer=setInterval(()=>{inspect(selected+1,true);if(selected===nodes.length-1)stop();},1500);
    };
    viewport.onpointerdown=event=>{
      if(event.target.closest('button') || event.button!==0)return;
      drag={x:event.clientX,y:event.clientY,tx,ty};viewport.setPointerCapture(event.pointerId);
      viewport.classList.add('flow-dragging');
    };
    viewport.onpointermove=event=>{if(drag){tx=drag.tx+event.clientX-drag.x;ty=drag.ty+event.clientY-drag.y;transform();}};
    viewport.onpointerup=viewport.onpointercancel=()=>{drag=null;viewport.classList.remove('flow-dragging');};
    viewport.onkeydown=event=>{
      if(event.target!==viewport)return;
      const moves={ArrowLeft:[60,0],ArrowRight:[-60,0],ArrowUp:[0,60],ArrowDown:[0,-60]};
      if(moves[event.key]){event.preventDefault();tx+=moves[event.key][0];ty+=moves[event.key][1];transform();}
      if(event.key==='Home'){event.preventDefault();fit();}
    };
    draw();
    return ()=>stop();
  }
  globalThis.AgentWorkflow = {build, render, mount, keepListNodeVisible};
})();
