# Skenario Video Demo — Material Continuity (± 5 menit)

Direkam dari **versi deployment**:
https://material-continuity-antek2-rl.cfapps.ap10.hana.ondemand.com

Login demo: `quality`, `engineering`, atau `planner` dengan password demo tim.

## Persiapan sebelum merekam

1. **Data online masih bersih**: belum ada approval, belum ada inject delay. Kalau sudah kotor,
   reset dengan `cf restage material-continuity-antek2-rl`. Penyimpanan Cloud Foundry tidak permanen,
   jadi data online kemungkinan kembali kosong setelah restage atau push. Jangan deploy ulang
   setelah persiapan, dan cek ulang datanya setelah restage.
2. **AI review sudah dijalankan sekali** di tab Agent Workflow (berbayar), supaya hasilnya tersimpan.
   Saat merekam cukup ditampilkan, jangan dijalankan ulang.
3. **Tab browser yang dibuka:**
   - Tab 1: `…/#public` (belum login)
   - Tab 2: Joule Web Client (sudah login IAS, mulai dengan New Conversation)
4. Zoom browser 110–125% supaya teks terbaca di video. Tutup notifikasi laptop.
5. Ganti user (quality → planner) di-*cut* saat editing supaya tidak makan waktu.
6. Siapkan cadangan: server lokal `python -m services.web --database data/local/demo-backup.sqlite3`
   dan hotspot HP.

---

## Adegan 1 — Pembuka & masalah (0:00 – 0:25)

**Tampilkan:** Dashboard publik (`#public`), diam sejenak.
**Sorot:** Judul "Dashboard Material Continuity".

> "Bayangkan sebuah pabrik perakitan. Satu komponen kritis, yaitu bearing, kirimannya terlambat.
> Reaksi pertama biasanya: beli saja pengganti. Masalahnya, **barang yang tersedia belum tentu
> siap dipakai**. Bearing pengganti harus terbukti sesuai spesifikasi, lolos uji, dan disetujui
> tim Quality. Material Continuity membantu pabrik menjawab: bisakah pengganti dipakai tepat
> waktu, dan bukti apa yang masih kurang?"

## Adegan 2 — Dashboard publik & notifikasi (0:25 – 0:50)

**Tampilkan:** Kartu metrik, lalu klik **ikon lonceng**.
**Sorot:**
- Kartu **"Stok habis: 4 Okt 2026"** dan **"Produksi terdampak: 700 EA, 7 production order"**
- Badge angka di lonceng, lalu daftar notifikasi

> "Ini dashboard publik. Semua pihak bisa melihatnya tanpa login. Stok bearing diprediksi habis
> **4 Oktober**, dan **700 unit di 7 production order** terancam. Notifikasi langsung memberi tahu:
> opsi resmi tidak mencukupi, satu kandidat ditolak, dan production release masih terblokir.
> Semua angka ini dihitung oleh kode, bukan ditebak oleh AI."

## Adegan 3 — Login & peran (0:50 – 1:05)

**Tampilkan:** Klik **Login**, scroll ke kartu peran.
**Sorot:** Empat kartu peran, terutama tanda ✓ dan ✕.

> "Ada tiga peran: Quality, Engineering, dan Production Planner. Masing-masing punya hak yang
> berbeda, dan hak itu ditentukan oleh server, bukan oleh browser. Kita masuk sebagai Quality
> Engineer."

**Aksi:** Klik **"Masuk sebagai Quality Engineer"**, isi password, login.

## Adegan 4 — Ringkasan kasus (1:05 – 1:40)

**Tampilkan:** Overview (metrik + notifikasi + tabel kasus), lalu klik **CASE-001** (tab Summary & Options).
**Sorot:**
- 4 kartu: **Stok siap pakai 300**, **Shortage pertama 4 Okt 2026**, **Cakupan opsi resmi 0 / 700**
- Tabel **"Approved recovery diperiksa terlebih dahulu"**
- Banner kuning **"Production release: Terblokir"**

> "Dari 320 bearing di gudang, hanya **300 yang bisa dipakai**, karena sisanya dialokasikan atau
> ditahan Quality. Sistem selalu memeriksa **opsi resmi dulu**: stok gudang lain, supplier yang
> disetujui, BOM alternatif, dan deviasi. Hasilnya, **tidak ada satu pun** yang bisa menutup 700 unit
> tepat waktu. Baru setelah itu sistem mempertimbangkan kandidat baru. Dan perhatikan banner ini:
> production release **selalu terblokir**, karena keputusan akhir tetap di tangan manusia."

## Adegan 5 — Bukti kandidat (1:40 – 2:20)

**Tampilkan:** Tab **Evidence Review**.
**Sorot:**
- **CAND-B**: baris Bore 30 mm → **Tidak sesuai**, badge **"Ditolak"**
- **CAND-A**: Bore 25 mm ✅, Load 16 kN ✅, **Lubricant → Belum diketahui**
- Klik link sumber **"Candidate_A_Datasheet_Rev2.pdf · p.2"**, PDF terbuka di halaman 2, lalu kembali

> "Setiap syarat teknis dibandingkan dengan bukti dokumen. **Kandidat B langsung ditolak**: lubangnya
> 30 milimeter, padahal butuh 25. **Kandidat A** cocok di ukuran dan beban, tapi belum ada bukti
> pelumasnya tahan suhu operasi. Sistem **tidak menganggapnya cocok**. Statusnya tetap *belum
> diketahui*. Dan setiap status bisa ditelusuri ke dokumen, revisi, dan halaman sumbernya. Ini
> halaman 2 datasheet-nya."

## Adegan 6 — Skenario & waktu kesiapan (2:20 – 2:55)

**Tampilkan:** Tab **Recovery Scenarios**.
**Sorot:**
- **Garis waktu "Barang datang ≠ siap dipakai"** di bagian atas: titik **Tiba 2 Okt** → **Stok habis 4 Okt** → **Siap pakai 7 Okt**, dengan celah merah dan tulisan **"Siap 3 hari 2 jam setelah stok habis"**
- Kartu **Rank #1: Original-part expedite → Layak**, lalu baca singkat **"Alasan ranking: Melindungi semua order · siap sebelum stok habis"**

> "Sekarang soal waktu. Kandidat A **tiba 2 Oktober**, sebelum stok habis. Tapi uji kualifikasinya,
> yaitu tes suhu di lab, review Engineering, lalu review Quality, baru selesai **7 Oktober**. Itu
> **tiga hari setelah** stok habis. Inilah inti masalahnya: *barang datang tidak sama dengan siap
> dipakai*. Sistem lalu membandingkan tiga skenario dan memberi ranking. Di kondisi ini,
> **mempercepat pengiriman komponen asli** menjadi pilihan terbaik karena melindungi semua order."

## Adegan 7 — Approval & aksi (2:55 – 3:35)

**Tampilkan:** Tab **Approval & Actions**.
**Aksi:**
1. Klik **"Approve qualification task"**
2. Klik **"Create mock QMS task"**, lalu tunjuk pesan **"Mock QMS task QMS-QUAL-… berhasil dibuat"**
3. Tunjuk tombol yang sekarang **nonaktif**

**Sorot:** Kolom Versi dan status **AUTHORIZED**, nomor QMS task, tombol nonaktif.

> "Quality Engineer menyetujui uji kualifikasi untuk syarat pelumas. Persetujuan ini **terikat ke
> versi kasus**, ke role, dan ke tugas yang spesifik. Lalu sistem membuat tugas di QMS. Di demo ini
> QMS-nya disimulasikan. Kalau tombol ditekan lagi, **tidak ada tugas ganda**, karena sistem memblokir
> duplikat. Dan ingat, menyetujui *uji* bukan berarti bearing *boleh dipakai*. Production release
> tetap terblokir."

## Adegan 8 — Perubahan data & approval basi (3:35 – 4:10)

**Tampilkan:** *(cut)* Logout, login sebagai **Planner**, buka tab **Summary**.
**Aksi:** Di **Inject delayed delivery**, pilih `PO-ORIGINAL-001`, ubah tanggal, lalu klik
**"Inject delay & hitung ulang"**.
**Sorot:**
- Banner biru **"Kasus diperbarui ke versi 2"**: Exposure 700 → 800 EA, 7 → 8 order, approval versi 1 tidak berlaku lagi
- Pindah ke tab **Approval & Actions**: approval lama sekarang **Terblokir** dengan alasan **"Versi kasus berubah"**

> "Sekarang kita masuk sebagai Production Planner. Ada kabar: kiriman komponen asli **mundur lagi**.
> Begitu tanggal diubah, sistem **langsung menghitung ulang**. Sekarang 800 unit dan 8 order terdampak,
> dan kasus naik ke **versi 2**. Yang penting: approval tadi **otomatis tidak berlaku lagi**, karena
> dibuat untuk versi lama. Tidak ada keputusan yang bisa dijalankan dengan data yang sudah basi."

## Adegan 9 — Agent workflow & AI (4:10 – 4:25)

**Tampilkan:** Tab **Agent Workflow**.
**Sorot:** Diagram node, lalu hasil **AI review yang tersimpan**.

> "Di balik layar, agent mengoordinasikan investigasi langkah demi langkah. Model AI dari
> **SAP AI Core** membaca dokumen dan menyusun penjelasan. Tapi semua angka dan aturan tetap dihitung
> oleh kode, dan AI tidak punya akses untuk menyetujui apa pun."

## Adegan 10 — Joule (4:25 – 4:50)

**Tampilkan:** Tab Joule. Ketik **"Is there a material shortage right now?"**
**Sorot:** Jawaban Joule (material, tanggal shortage, exposure, order terdampak).

> "Kasus yang sama juga bisa ditanyakan lewat **SAP Joule**. Manajer cukup bertanya *ada shortage
> atau tidak*, dan Joule menjawab langsung dari backend Material Continuity. Joule hanya membaca data.
> Keputusan tetap lewat aplikasi, oleh orang dengan peran yang tepat."

Prompt Joule cadangan:
- "Give me a briefing on the current material continuity case"
- "What recovery options are available for the current case?"
- "What is the approval status of the current case?"

## Adegan 11 — Penutup (4:50 – 5:00)

**Tampilkan:** Kembali ke dashboard publik.

> "Material Continuity: keputusan pemulihan material yang bisa ditelusuri, tepat waktu, dan tetap
> dikendalikan manusia. Terima kasih."

---

## Yang jangan diucapkan

- ❌ **"Data pabrik asli."** Datanya sintetis. Kalau perlu, sebut "data simulasi".
- ❌ **"Biaya 7.500 rupiah/dolar."** Biaya di aplikasi tidak punya mata uang. Kalau disebut, cukup
  "biaya tambahan".
- ❌ **"Waktu keputusan sudah terbukti 50% lebih cepat."** Itu target pilot di proposal, bukan hasil
  yang sudah terbukti.
- ❌ **"AI yang memutuskan."** AI hanya membaca dan menjelaskan. Kode yang menghitung, manusia yang
  memutuskan.

## Tips editing

- Total narasi sekitar 620 kata ≈ 4:45 menit bicara, jadi ada ruang 15 detik untuk jeda dan transisi.
- Pakai **zoom-in atau lingkaran sorot** saat menunjuk angka penting: 4 Okt 2026, 700 EA, 30 mm,
  garis waktu 2 → 4 → 7 Okt, banner versi 1 → 2.
- Proses login dan loading di-*cut*.
- Kalau video harus lebih pendek (± 3 menit), buang adegan 3, 9, dan sebagian adegan 4.
