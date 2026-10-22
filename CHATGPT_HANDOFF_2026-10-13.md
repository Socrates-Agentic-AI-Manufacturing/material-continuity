# Material Continuity — Handoff Progress dan Rencana Web MVP

Tanggal pembaruan: **13 Oktober 2026, Asia/Jakarta**

Tujuan: dokumen mandiri untuk dikirim ke chat GPT yang sebelumnya membantu menyusun konteks/proposal, agar memahami implementasi yang telah selesai, keputusan pengguna terbaru, dan rencana berikutnya.

> Snapshot ini dibuat sebelum implementasi functional web pada hari yang sama.
> Setelah feedback pengguna, local web/API, SQLite persistence, demo sessions,
> approval/action UI, dan read-only document browsing sudah ditambahkan; total
> test sekarang 116. Lihat tracker dan Session Progress Log terbaru di
> `PROJECT_CONTEXT.md` untuk progress setelah snapshot ini. Isi baseline di bawah
> sengaja dipertahankan agar riwayat handoff tidak berubah diam-diam.

Dokumen ini merangkum `PROJECT_CONTEXT.md`, repository lokal, hasil test, dan pembahasan terbaru dengan pengguna. Dokumen proposal asli tidak diperiksa ulang dalam sesi ini; bagian proposal di bawah mengikuti konteks proyek yang sudah diberi label `[PROPOSAL]`.

Status dalam dokumen dibedakan menjadi:

- **TERIMPLEMENTASI**: tersedia dalam kode dan diuji.
- **KEPUTUSAN PENGGUNA**: arahan eksplisit pengguna yang harus diikuti.
- **RENCANA/REKOMENDASI**: arah pembahasan yang belum menjadi implementasi atau keputusan teknis final.
- **BELUM TERVERIFIKASI**: akses, integrasi, atau asumsi yang belum dibuktikan.

## 1. Ringkasan yang perlu diketahui terlebih dahulu

Material Continuity sudah memiliki deterministic core, synthetic dataset, 12 PDF evidence corpus, versioned recovery case, approval gate, mock QMS action adapter, serta workflow lokal Evidence Specialist dan Recovery Supervisor.

Implementasi terakhir telah di-commit dan di-push ke repository organisasi. Semua **98 test** lulus ketika diverifikasi kembali pada 13 Oktober 2026.

**Belum ada web UI, HTTP backend untuk UI, database persisten, autentikasi pengguna nyata, live retrieval, atau pemanggilan LLM live.** Paket agent saat ini adalah workflow Python dengan mock/fixture adapters dan role prompts yang disiapkan untuk integrasi berikutnya.

Arahan pengguna terbaru: **langsung membangun UI yang terhubung ke sistem dan mendekati MVP final; tidak perlu mendahulukan demo runner CLI end-to-end yang terpisah.** Alur demonstrasi dan acceptance tetap harus tersedia melalui web.

## 2. Identitas proyek dan repository

| Item | Nilai |
|---|---|
| Nama proyek | Material Continuity |
| Track | Intelligent Manufacturing, mengikuti konteks proyek |
| Tahap hackathon | Lolos final |
| Repository aktif | https://github.com/Socrates-Agentic-AI-Manufacturing/material-continuity.git |
| Branch | `main` |
| Commit implementasi terakhir | `d090dfb` — `feat(agents): add local recovery supervisor` |
| Lokasi workspace | `D:\TATAN_KULIAH_PASSED\SEMESTER 7 (ONGOING)\Binus-Hack` |
| Konteks arsitektur utama | `PROJECT_CONTEXT.md` |
| Runtime lokal | Python 3.11+, dataclasses, unittest |
| Dependency aplikasi saat ini | Tidak ada third-party runtime dependency di `pyproject.toml` |

Remote lama `SimforianusJonathan/material-continuity` sudah diganti. Gunakan repository organisasi untuk fetch/push selanjutnya.

Pengguna meminta commit profesional dengan Conventional Commits dan **tidak perlu signed commit**. Commit dapat menggunakan `git -c commit.gpgsign=false commit ...` tanpa mengubah konfigurasi signing global.

Sebelum pembuatan dokumen handoff ini, working tree bersih dan `main` sinkron dengan `origin/main`. File handoff dan pembaruan konteks dari sesi ini adalah perubahan dokumentasi baru; jangan menganggap keduanya sudah di-push.

## 3. Sistem yang kita propose sebenarnya apa?

Material Continuity adalah workflow pendukung keputusan pemulihan produksi ketika material kritis terlambat, tidak tersedia, atau terkena quality hold.

Pertanyaan intinya:

> Apakah material alternatif dapat memenuhi persyaratan, menyelesaikan qualification, dan menjadi siap digunakan sebelum jendela pemulihan produksi berakhir? Bukti dan persetujuan apa yang masih diperlukan?

Saat pengguna menyebut “sistem penilaian”, maksud yang dibahas adalah **penilaian kelayakan material alternatif dan recovery options berdasarkan bukti, persyaratan, waktu, biaya, dan dampak produksi**.

Belum ada keputusan membuat skor numerik tunggal, ranking berbobot, atau membiarkan LLM menentukan keselamatan material. Sistem saat ini mengeluarkan status requirement dan perbandingan skenario yang terstruktur.

Prinsip utamanya:

1. Material tersedia belum tentu siap dipakai.
2. Kandidat yang tiba sebelum shortage belum tentu selesai qualification sebelum shortage.
3. Bukti yang hilang atau tidak berlaku harus terlihat sebagai `UNKNOWN`.
4. Hard mismatch menolak kandidat.
5. Engineering dan Quality tetap memegang otoritas review/release.
6. Approval terikat pada versi dan hash kasus yang direview.
7. Perubahan bukti atau decision state dapat membuat approval sebelumnya stale.

Pembagian tanggung jawab:

| Pemilik | Tanggung jawab |
|---|---|
| LLM/agent, setelah integrasi live | Menginterpretasi dokumen, memilih tool, mengoordinasikan investigasi, menyusun penjelasan dengan bukti |
| Deterministic code | Stock arithmetic, unit comparison, hard constraints, qualification timing, scenario impact, approval policy, idempotency |
| Manusia | Review Engineering/Quality, approval tindakan sesuai role, final release authority |

## 4. Scope MVP yang tetap dipertahankan

Scope data canonical:

- Satu bearing family yang digunakan langsung dalam assembly BOM.
- Tiga kandidat material.
- Dua assembly BOM.
- Sepuluh production orders.
- Dua belas dokumen technical/quality berbasis teks.
- Satu plant utama, network stock lookup, supplier fixtures, dan test/resource calendars.
- Synthetic enterprise data dan mock qualification/QMS output.

Arsitektur target proposal mencakup Bedrock inference, S3, Bedrock Knowledge Base, AgentCore Runtime/Gateway, controlled tools, approval/action, review UI, serta EventBridge/Lambda/observability.

Live SAP write-back, automatic BOM release, real physical qualification, dan production-scale factory deployment tetap di luar scope MVP asli. Keinginan menghasilkan MVP layak dipakai tidak otomatis memperluas scope menjadi pengganti sistem release pabrik nyata.

## 5. Progress implementasi terverifikasi

| Komponen | Status | Implementasi utama |
|---|---|---|
| Exposure engine | TERIMPLEMENTASI | Menghitung usable stock, dated demand, receipt, shortage, dan affected orders |
| Recovery option discovery | TERIMPLEMENTASI | Menelusuri approved paths sesuai urutan sebelum kandidat unqualified |
| Requirement comparison | TERIMPLEMENTASI | Unit normalization, current revision/applicability checks, konflik bukti, hard rejection |
| Qualification graph | TERIMPLEMENTASI | Dependency DAG, resource calendars, sequential/parallel tasks, critical path, unresolved timing |
| Recovery simulation | TERIMPLEMENTASI | Ready date, quantity/order impact, incremental cost, scenario state; feasibility terpisah dari authorization |
| Recovery-case state | TERIMPLEMENTASI | Immutable snapshots, version increments, canonical SHA-256 hashes, source versions, approval/action history |
| Approval gate | TERIMPLEMENTASI | Role, identity, action scope, expiry, version/hash, supplied source freshness, used idempotency key |
| QMS action adapter | TERIMPLEMENTASI, MOCK | Membuat qualification task/receipt deterministik; duplicate execution blocked; production release false |
| Document corpus | TERIMPLEMENTASI, SYNTHETIC | 12 PDF, 35 halaman, metadata/provenance, manifest/checksum |
| Evidence pipeline contract | TERIMPLEMENTASI | Structured extraction validation, exclusions, bridge ke comparison engine |
| Evidence Specialist | TERIMPLEMENTASI LOKAL | Fixture retrieval, requirement mapping, gap detection, procedure lookup, trace, role prompt |
| Recovery Supervisor | TERIMPLEMENTASI LOKAL | Ordered workflow/tool calls, branch no exposure/approved sufficient/candidates required, case creation dan summary |
| Web UI | BELUM | Belum ada aplikasi web yang dibangun |
| HTTP API/backend integration | BELUM | Core masih dipanggil sebagai library/CLI/test |
| Persistence | BELUM | Case domain model tersedia; belum database/storage adapter |
| User authentication | BELUM | Principal/role model tersedia; belum session/login/token verification nyata |
| Live LLM/runtime | BELUM | Role prompts tersedia; belum LLM invocation atau adaptive model tool-calling loop |
| Live document retrieval/extraction | BELUM | Saat ini mengambil prepared extraction fixtures, bukan mengekstrak PDF pada runtime |
| Cloud infrastructure | BELUM TERVERIFIKASI/TERINTEGRASI | AWS dan SAP account access tidak dianggap sudah terkonfirmasi |

### Batas penting agar progress tidak disalahartikan

- “Evidence Specialist selesai” berarti workflow lokal dan kontraknya selesai, bukan Bedrock-backed agent sudah berjalan.
- “Recovery Supervisor selesai” berarti orchestration Python atas controlled tools sudah berjalan, bukan model AI sudah membuat keputusan tool secara adaptif.
- Nama `AuthenticatedPrincipal` tidak berarti sistem login sudah terimplementasi. Data identitas/role saat ini diberikan oleh caller.
- Source-freshness gate membandingkan supplied source snapshots. Mengambil snapshot terbaru dari sistem eksternal masih membutuhkan connector.
- Idempotency saat ini diperiksa terhadap action receipts dalam case yang diberikan. Untuk banyak request paralel atau server restart, masih perlu persistence dan atomic write/uniqueness enforcement.
- Qualification-task record/receipt saat ini mock; tidak dibuat di QMS perusahaan nyata.
- Qualification schedule adalah rencana, bukan bukti fisik test telah dilakukan dan lulus.
- PDF corpus merupakan synthetic fixtures. Angka/dokumen bukan spesifikasi vendor nyata yang boleh dipakai di pabrik.
- Scenario timing saat ini dimuat dari fixture. Saat input web dapat berubah, simulation inputs harus mengikuti qualification/exposure snapshot yang sama dan tidak terus menggunakan tanggal fixture yang lama.

## 6. Hasil canonical scenario

Tanggal di bagian ini adalah **tanggal skenario sintetis yang tetap**, bukan kondisi produksi aktual pada 13 Oktober 2026. Jangan mengganti fixture date ke tanggal hari ini tanpa memperbarui semua fixture/test terkait secara konsisten.

| Aspek | Hasil canonical |
|---|---|
| Material | `MAT-BRG-001`, assembly bearing 25 mm |
| Gross stock | 320 EA |
| Allocation | 10 EA |
| Quality hold | 10 EA |
| Usable stock | 300 EA |
| Shortage pertama | 4 Oktober 2026 |
| Order terdampak | 7 |
| Total unserved quantity | 700 EA |
| Timely approved coverage | 0 dari 700 EA |

Approved paths ditelusuri dalam urutan:

```text
network stock
→ approved source
→ approved equivalent
→ alternate BOM
→ valid deviation
→ unqualified candidates
→ original expedite
→ production resequencing
```

### Penilaian kandidat

| Requirement | Candidate A | Candidate B |
|---|---|---|
| Bore = 25 mm | 25 mm, MATCH | 30 mm, MISMATCH; hard reject |
| Dynamic load >= 14 kN | 16 kN, MATCH | 18 kN, MATCH |
| Application-specific lubricant temperature suitability | UNKNOWN; bukti belum tersedia | MATCH dalam fixture |
| Plant qualification release | BLOCKED | BLOCKED |
| Candidate decision | Conditional/pending evidence or release | Rejected hard mismatch |

Candidate C juga muncul dalam supervisor workflow. Bukti terstruktur yang lengkap belum tersedia untuk C, qualification graph-nya belum tersedia, dan prior deviation sudah berakhir 25 September 2026. Candidate C tetap conditional; ketidaklengkapannya tidak boleh menjadi MATCH.

Candidate A tiba 2 Oktober 2026 pukul 02:00 UTC, sedangkan qualification path selesai terjadwal 7 Oktober 2026 pukul 02:00 UTC. Kandidat datang sebelum shortage tetapi readiness setelah shortage.

### Perbandingan skenario

| Skenario | Kesiapan dalam fixture | Protected quantity | Sisa exposed | State |
|---|---|---:|---:|---|
| Candidate A + qualification | 7 Okt 2026 02:00 UTC | 400 EA | 300 EA / 3 orders | PARTIAL |
| Original-part expedite | 4 Okt 2026 00:00 UTC | 700 EA | 0 EA | FEASIBLE |
| Production resequencing | 4 Okt 2026 00:00 UTC | 200 EA | 500 EA / 5 orders | PARTIAL |

Nilai cost tersedia sebagai integer cents dalam fixtures. Currency untuk tampilan harus dipastikan sebelum diberi simbol mata uang; jangan mengasumsikan Rupiah atau Dollar tanpa keputusan.

Semua scenario feasibility bukan authorization. Production release tetap tidak diotorisasi oleh output agent atau mock task.

## 7. Evidence dan case-version rules

Requirement states:

- `MATCH`: bukti applicable dan current mendukung requirement.
- `MISMATCH`: bukti current menunjukkan pelanggaran requirement.
- `UNKNOWN`: bukti hilang, unsupported, stale, conflicting, atau tidak applicable.
- `BLOCKED`: bukti menunjukkan release/qualification gate belum dipenuhi.

Bukti minimal menyimpan candidate/property/value/unit, document identity, revision, current revision, page/location, dan applicability. Confidence extraction tidak menggantikan bukti dan tidak menjadi izin release.

Case hash menggunakan SHA-256 atas canonical JSON yang mencakup case identity, version, previous hash, dan decision content. Approvals/action receipts disimpan terpisah tetapi mengacu pada exact case version/hash.

Case version berubah bila decision content atau tracked source state berubah. No-op update tidak menambah version. Append approval/action tidak sendiri mengubah decision version.

Approval gate memeriksa:

- Approval ada dan case reference tepat.
- Approver identity dan role cocok.
- Role mengizinkan action dan scope approval cocok.
- Approval sudah aktif dan belum expired.
- Case version/hash masih current.
- Supplied latest source versions cocok dengan case snapshot.
- Idempotency key belum digunakan.

Roles yang sudah ada:

| Role | Permitted action saat ini |
|---|---|
| `ENGINEERING_REVIEWER` | `CREATE_QUALIFICATION_TASK` |
| `QUALITY_ENGINEER` | `CREATE_QUALIFICATION_TASK` |
| `PRODUCTION_PLANNER` | `AUTHORIZE_RESEQUENCING` |

Action adapter yang sudah tersedia hanya mock `create_qualification_task`; adanya action enum resequencing tidak berarti resequencing adapter telah dibuat.

## 8. Corpus dan cara menjalankan sistem sekarang

PDF corpus:

```text
Candidate_A_Datasheet_Rev2.pdf
Candidate_A_Certificate.pdf
Candidate_B_Datasheet.pdf
Candidate_C_Datasheet.pdf
Engineering_Drawing_Assembly_A.pdf
Engineering_Drawing_Assembly_B.pdf
Bearing_Application_Requirements.pdf
Qualification_SOP_Temperature.pdf
Qualification_SOP_Load.pdf
Approved_Supplier_List.pdf
Existing_Deviation.pdf
Quality_Release_Procedure.pdf
```

Lokasi: `data/documents/`, dengan `manifest.json`. Generator ada di `scripts/generate_document_corpus.py`, semantic validator di `scripts/validate_document_corpus.py`. Utilitas PDF memerlukan library PDF saat build/validation; aplikasi deterministic core tetap tidak memerlukan third-party runtime packages.

Stable locations contoh:

- Candidate A revision 2: bore page 2, load page 3, missing lubricant application evidence page 4.
- Candidate B revision 1: bore page 2, load page 3, lubricant evidence page 4.

CLI yang sudah tersedia:

```powershell
python -m core.exposure --material MAT-BRG-001 --as-of 2026-09-29T00:00:00+00:00
python -m core.recovery_options --material MAT-BRG-001 --required-quantity 700 --need-by 2026-10-04 --as-of 2026-09-29
python -m core.requirements --candidate CAND-A
python -m core.requirements --candidate CAND-B
python -m core.qualification --candidate CAND-A
python -m core.simulation --material MAT-BRG-001 --as-of 2026-09-29T00:00:00+00:00 --shortage-at 2026-10-04T00:00:00+00:00
python -m core.case_state --case-id CASE-001
python -m unittest discover -s tests -v
```

Agent workflows digunakan melalui library functions dan integration tests. Belum ada satu CLI yang menghubungkan supervisor, approval, action, duplicate replay, dan stale revision dalam satu run. Pengguna sudah memutuskan agar kebutuhan demonstrasi berikutnya diwujudkan melalui UI.

## 9. Riwayat commit implementasi

| Commit | Pesan |
|---|---|
| `25f609c` | `feat(core): add deterministic exposure engine` |
| `ab4efdf` | `feat(core): add ordered recovery option discovery` |
| `a8af886` | `feat(core): add deterministic requirement comparison` |
| `06abf19` | `feat(core): add qualification dependency scheduling` |
| `75a937b` | `feat(core): add deterministic recovery simulation` |
| `996164c` | `feat(core): add versioned recovery case` |
| `ac96eeb` | `feat(evidence): add synthetic document corpus` |
| `4c264da` | `feat(core): enforce deterministic approval gate` |
| `39891f9` | `feat(core): add approval-gated action adapter` |
| `d979bc7` | `feat(evidence): add structured comparison bridge` |
| `9cbfa41` | `feat(agents): add mock-backed evidence specialist` |
| `d090dfb` | `feat(agents): add local recovery supervisor` |

Semua implementasi sampai `d090dfb` sudah di-push ke remote organisasi.

## 10. Informasi baru dari panitia: SAP dan mentoring

Pengguna memberikan PDF email mentoring dan manual:

https://hackathon-manual.cfapps.ap10.hana.ondemand.com/

Manual tersebut sudah dibaca pada 13 Oktober 2026. Isinya tutorial fasilitas SAP untuk registered hackathon participants:

- Aktivasi SAP IAS account dan login BTP cockpit.
- Cloud Foundry CLI, team space, dan deployment aplikasi.
- Pengambilan AI Core/Joule service credentials sesuai team slug.
- Model inference melalui SAP AI Core / Generative AI Hub.
- Joule capability authoring/deployment.

Manual menyebut shared AI Core services, team-specific app spaces, dan total quota Cloud Foundry team space 1 GB. Detail akses/deployment harus dicek lagi ketika integrasi dilakukan.

**Tidak ada account activation, credential retrieval, deployment, atau perubahan provider yang sudah dilakukan oleh agent.** Pengguna memilih melewati verifikasi SAP dahulu dan meminta commit/push Recovery Supervisor, yang sekarang sudah selesai.

Manual SAP tidak membuktikan bahwa AWS Bedrock/S3 access tersedia. Tidak ada keputusan mengganti arsitektur AWS dengan SAP AI Core/Joule. Provider/runtime deployment masih perlu diverifikasi dan diputuskan berdasarkan fasilitas tim serta ketentuan proposal/panitia.

Email mentoring menyebut periode mentoring 1–30 Oktober 2026, bersifat opsional dan tidak memengaruhi penilaian; Demo Day 31 Oktober 2026. Deadline pertanyaan yang tertulis adalah 5 Oktober pukul 16.00 WIB, sudah lewat pada saat diskusi ini. Informasi tersebut berasal dari email yang diberikan pengguna, bukan peraturan penilaian lengkap.

Jangan mengambil credentials hanya karena URL keybroker ada di manual. Jangan menyalin secrets ke handoff, prompt, log, atau repository.

## 11. Keputusan pengguna terbaru dan perubahan prioritas

### KEPUTUSAN PENGGUNA

1. Verifikasi akses SAP ditunda dahulu.
2. Recovery Supervisor di-commit/push tanpa signing; sudah selesai.
3. Demo runner lokal yang terpisah tidak perlu diprioritaskan.
4. Langsung menuju web UI yang dekat dengan final, dengan target MVP yang bisa dipakai untuk workflow review.
5. Core architecture tidak boleh dirombak atau diberi dependency baru tanpa alasan teknis konkret.
6. Handoff ini dibuat agar chat GPT lama memahami progress dan rencana sekarang.

### RENCANA/REKOMENDASI YANG SUDAH DIBAHAS

- UI harus terhubung ke backend/core; bukan hanya mockup statis.
- Upload dokumen dan extraction dari actual document content menjadi jalur data awal yang jelas.
- Gunakan ingestion terkontrol, versioned evidence, dan runtime retrieval.
- Data volatile diperbarui dari connector/API dan dicek ulang sebelum action.
- Background sync ditambahkan setelah sumber data dan freshness policy jelas.
- LLM memilih tool/interprets evidence, sedangkan comparison/approval tetap deterministic.

Nama frontend framework, backend framework, database, model provider, scraping targets, sync interval, dan scoring/ranking weights **belum diputuskan**.

## 12. Rencana final web: enam area fungsional

Susunan ini merupakan rekomendasi terbaru untuk dibahas dan diimplementasikan. Belum ada frontend code.

| Area | Tujuan dan isi |
|---|---|
| Overview / Cases | Melihat material disruptions, shortage deadline, order impact, status kasus, dan review yang tertunda |
| Recovery Case | Detail material/stock/demand, approved-path discovery, kandidat, case version, dan ringkasan investigasi |
| Evidence Review | Requirement matrix per kandidat; normalized values; MATCH/MISMATCH/UNKNOWN/BLOCKED; dokumen, revisi, halaman, applicability, dan gaps |
| Recovery Scenarios | Compare substitute + qualification, expedite, resequencing; timeline, arrival vs readiness, cost, protected/deferred production |
| Approval & Actions | Review sesuai role, approve qualification-task action, rejection/block reasons, expiry, stale authorization, dan QMS receipt |
| Documents & Data | Upload dokumen, metadata/revisions, extraction/indexing state, data source, last updated, sync status, dan error handling |

Navigation yang disarankan:

```text
Overview
Recovery Cases
  └─ Recovery Case detail
       ├─ Summary & Options
       ├─ Evidence Review
       ├─ Recovery Scenarios
       └─ Approval & Actions
Documents & Data
```

Jadi enam area fungsi tidak berarti enam menu sidebar. Sidebar cukup tiga entry utama. Audit history dan agent/tool activity ditampilkan di dalam kasus.

Prioritas informasi bagi reviewer:

```text
kapan stok habis
→ kandidat memenuhi requirement atau tidak
→ bukti apa yang belum tersedia
→ kapan kandidat siap dipakai
→ opsi mana melindungi produksi
→ tindakan apa yang boleh disetujui
```

### Perilaku UI yang perlu diwujudkan

- Status evidence dapat ditelusuri ke source dan page; reviewer dapat membuka dokumen terkait.
- Candidate B terlihat rejected, dengan alasan bore mismatch yang konkret.
- Candidate A tetap menunjukkan gap temperature/lubricant dan release gate.
- Timeline memisahkan supplier arrival, test, review, qualification readiness, dan shortage.
- Approval/action yang blocked harus menampilkan alasan, bukan sekadar disabled button tanpa penjelasan.
- Setelah revision/source berubah, case version bertambah dan approval lama terlihat stale.
- Repeated action tidak membuat QMS task kedua.
- Case dan receipt tetap tersimpan saat halaman refresh atau aplikasi restart setelah persistence ditambahkan.
- Prototype data mode dan live data mode dibedakan secara jujur; synthetic data tidak ditampilkan sebagai data plant nyata.
- Loading, empty, missing-evidence, failed-extraction, failed-sync, dan stale-data states termasuk dalam desain.

Ini adalah product behavior yang direncanakan, bukan fitur yang sudah selesai.

## 13. Rencana acquisition, freshness, dan retrieval

Jawaban arsitektural yang dibahas adalah kombinasi **controlled ingestion + runtime retrieval + live checks untuk data volatile**.

| Jenis data | Jalur yang disarankan | Freshness behavior |
|---|---|---|
| Datasheets, drawings, certificates, SOP | Upload atau approved document repository sync | Version/hash-aware ingestion saat revisi berubah |
| Stock, supplier ETA, production orders | Connector/API yang authoritative; local fixture tetap untuk demo | Refresh saat kasus dibuka dan sebelum relevant action |
| QMS release/deviations | Official QMS/controlled source | Cek validity, current state, dan effective dates sebelum action |
| Public supplier information | Search/scraping terbatas dari verified sources | Discovery lead; jangan otomatis menjadi release/qualification evidence |

Alur dokumen yang diinginkan:

```text
upload/source connector
→ validate file + identify document/revision
→ save immutable source/version metadata
→ extract text dengan page boundaries
→ index evidence
→ retrieve saat investigator membuka kasus
→ extract/map structured claims dengan citations
→ deterministic comparison
→ versioned recovery case
→ human review/approval
```

Pemisahan konsep:

- **Sync/ingestion** memperbarui data yang tersimpan dan diindeks.
- **Retrieval** mengambil bukti yang relevan untuk kasus pada runtime.
- **LLM extraction/synthesis** menginterpretasi retrieved content; tidak menjadikan model memory sebagai sumber fakta.
- **Source validation/freshness** memastikan version state yang direview masih berlaku sebelum action.

Scraping luas belum diperlukan sebagai step pertama. Sumber awal MVP sudah bisa berupa 12 synthetic PDFs dan controlled uploads. Stock/internal QMS tidak bisa diasumsikan tersedia dari web publik.

Jika web search dipakai, setiap informasi yang ingin dipromosikan menjadi evidence perlu source URL/document identity, revision bila tersedia, retrieval timestamp, applicability, dan review rule. Fakta tanpa dukungan memadai tetap UNKNOWN.

Tidak ada scheduler, scraper, auto-sync connector, atau LLM web-search integration yang sudah dibuat. Sync cadence belum ditentukan; interval perlu mengikuti sumber dan toleransi stale data, bukan angka acak.

Referensi teknis yang digunakan dalam diskusi:

- Bedrock incremental source synchronization: https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-sync.html
- Bedrock retrieval and source metadata: https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-retrieve.html

Referensi tersebut mendukung mekanisme target, bukan bukti bahwa akun tim sudah memiliki fasilitasnya.

## 14. Gap menuju MVP web yang layak dipakai

Teruji secara unit/integration bukan berarti aplikasi end-user sudah siap dipakai. Gap utama saat ini:

1. **Web/API integration**: exposed contracts untuk membaca kasus, menjalankan investigasi, menyimpan approval, mengeksekusi mock task, dan menerima document update.
2. **Persistence**: durable case/version/source/approval/action records dan atomic idempotency.
3. **Identity**: authenticated sessions dan role enforcement di server; jangan mempercayai role yang dikirim browser sebagai otoritas.
4. **Actual ingestion/extraction**: baca isi PDF yang diupload dengan provenance nyata; prepared fixture rows tidak boleh dipresentasikan sebagai hasil LLM extraction live.
5. **Live AI**: model invocation, schema validation, bounded failures/retries, dan grounded outputs. Provider belum diputuskan ulang.
6. **State consistency**: simulation inputs, qualification graph, evidence, stock, dan approval harus merujuk snapshot kasus yang konsisten.
7. **Operational UX**: clear freshness, error/retry behavior, file validation, readable citations, dan audit visibility.
8. **Acceptance melalui web**: one coherent scenario bisa dilakukan reviewer dari case hingga action/stale approval tanpa perlu terpisah-pisah menjalankan test.
9. **Deployment**: target host, config/secrets handling, dan cloud permissions belum selesai.

Untuk hackathon, synthetic enterprise data dan mock QMS action memang diperbolehkan dalam scope. Untuk penggunaan dengan keputusan produksi nyata, real sources, human process, dan plant validation tetap dibutuhkan.

## 15. Urutan implementasi berikutnya yang direkomendasikan

Urutan ini mengikuti keputusan pengguna untuk UI-first, sambil menjaga core yang sudah ada.

### Langkah A — Tetapkan contracts dan batas web MVP

- Tentukan frontend/backend/persistence dengan alasan teknis yang sesuai repository dan deployment constraints.
- Reuse existing typed models dan engines.
- Dokumentasikan API/data contracts sebelum menghubungkan semua screen.
- Tentukan mode synthetic demo secara eksplisit.

### Langkah B — Bangun vertical slice web pertama

- Case list → open case → run Recovery Supervisor.
- Render exposure, approved-path results, candidate evidence matrix, dan scenario timeline dari backend output.
- Tampilkan source citations dan case version.
- Jangan menjalankan stock arithmetic/approval enforcement hanya di browser.

### Langkah C — Sambungkan review, approval, dan action

- Tambahkan persistence dan authenticated reviewer identity.
- Server memvalidasi role, scope, version/hash, expiry, sources, idempotency.
- Buat mock qualification task dan simpan receipt.
- Demonstrasikan duplicate block dan production release yang tetap blocked.

### Langkah D — Documents & Data workflow

- Upload new/revised PDF, simpan version metadata, dan lakukan actual extraction.
- Jalankan re-investigation dan update case secara konsisten.
- Tampilkan stale approval saat sumber berubah.
- Tambahkan sync/status/freshness controls sesuai kebutuhan sumber.

### Langkah E — Integrasi cloud dan final verification

- Verifikasi fasilitas AWS/SAP ketika pengguna siap.
- Sambungkan live inference/retrieval sesuai keputusan provider dan proposal.
- Uji canonical scenario melalui UI, termasuk failure states.
- Deploy dan verify akses aplikasi.

Tidak perlu membuat autonomous web scraper sebelum web review workflow dan evidence ingestion berhasil.

## 16. Definition of done yang diusulkan untuk web MVP

Reviewer dapat:

1. Membuka atau membuat disruption case dengan data yang jelas.
2. Melihat shortage dan production orders terdampak yang dihitung backend.
3. Melihat approved paths telah dievaluasi sebelum kandidat alternatif.
4. Membandingkan kandidat dengan requirement-level citations.
5. Melihat hard mismatch rejection dan UNKNOWN gaps.
6. Membandingkan tiga skenario, termasuk arrival versus actual readiness.
7. Menyetujui qualification task sesuai role dan current case version.
8. Mendapat satu mock QMS task receipt tanpa duplicate writes.
9. Melihat production release tetap blocked.
10. Mengupload/update source revision dan membuka case version baru.
11. Melihat previous approval stale dan execution attempt blocked.
12. Memuat kembali case/receipt dari storage, bukan kehilangan state ketika reload.

Authenticity requirements untuk presentasi:

- Label synthetic fixtures dan mock QMS jelas.
- Jangan mengklaim live Bedrock/SAP/ERP integration bila belum berjalan.
- Jangan mengklaim pilot time reduction 50% sudah terbukti; itu target proposal, bukan achieved result.
- Jangan mengklaim agent mengautorisasi produksi atau melakukan physical qualification.

## 17. Keputusan yang masih perlu dibahas dengan chat GPT lama

- Apakah pembagian enam area fungsi dan tiga menu sidebar paling sesuai kebutuhan reviewer?
- Minimum API/persistence/auth yang dibutuhkan agar web usable tanpa scope creep?
- Cara memenuhi unsur agentic pada final demo ketika live model/runtime tersedia, sambil menjaga deterministic boundaries?
- Penempatan fitur upload/revision/freshness yang mudah dipahami pengguna?
- Bagaimana memasukkan SAP fasilitas panitia tanpa diam-diam mengganti komitmen arsitektur AWS?
- Apakah scenario comparison cukup non-ranked atau membutuhkan ranking transparan? Belum ada scoring weights yang disetujui.
- Prioritas acceptance tests untuk review/action/version-update melalui web?

## 18. Instruksi untuk GPT penerima handoff

Gunakan dokumen ini sebagai progress update atas context yang sebelumnya kamu bantu buat.

- Jangan menyarankan bootstrap ulang deterministic core; komponen itu sudah tersedia dan teruji.
- Jangan menganggap UI, database, real authentication, live retrieval, atau live LLM sudah dibuat.
- Jangan memprioritaskan standalone CLI demo runner; pengguna memilih langsung ke UI.
- Pertahankan recovery-case workflow, explicit UNKNOWN/MISMATCH/BLOCKED, provenance, qualification timing, dan human authorization.
- Bedakan keputusan pengguna dari rekomendasi yang masih perlu dinilai.
- Jangan mengganti AWS dengan SAP atau memilih dependency/framework tanpa alasan teknis yang konkret.
- Jika menyarankan perubahan, jelaskan apa yang dapat direuse, apa yang baru, dan bagaimana perubahan diuji.
- Bila perlu mengubah konteks proyek, perbarui progress tracker dan session log tanpa menghapus sejarah.

Permintaan lanjutan yang dapat digunakan di chat GPT lama:

> Baca handoff ini seluruhnya. Evaluasi rencana web MVP terhadap proposal Material Continuity yang sebelumnya kita susun. Fokuskan jawaban pada struktur UI, minimum backend/persistence/auth, ingestion dan freshness, serta urutan implementasi agar MVP dekat dengan final. Pertahankan komponen yang sudah selesai. Tandai jelas mana keputusan yang sudah ada, mana rekomendasi baru, dan mana risiko/gap yang masih perlu ditangani. Jangan menganggap mock agent saat ini sudah menjalankan LLM live.
