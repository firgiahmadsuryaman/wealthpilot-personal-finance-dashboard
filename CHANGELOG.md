# Catatan Perubahan

Perubahan penting WealthPilot dicatat berdasarkan versi.

## 0.3.0 — Penguatan ledger dan sumber data

- Memastikan koneksi SQLite selalu ditutup dan transaksi database di-rollback saat terjadi exception.
- Memindahkan pemanggilan provider keluar dari transaksi tulis SQLite.
- Memvalidasi kronologi kas dan kuantitas sebelum transaksi disimpan atau penghapusan disetujui.
- Memvalidasi waktu transaksi, waktu harga, tanggal target, dan batas biaya.
- Menggunakan timestamp quote terakhir dari Twelve Data bila tersedia.
- Menambahkan fallback snapshot tersimpan yang diberi status `stale` saat provider gagal.
- Menambahkan penyuntingan transaksi dengan validasi ulang ledger.
- Menambahkan ekspor transaksi CSV UTF-8 yang ramah spreadsheet dan mitigasi formula injection pada catatan.
- Menambahkan ekspor JSON untuk seluruh tabel data lokal tanpa menyertakan kunci API.
- Menambahkan endpoint favicon dan memperbaiki label presisi waktu quote di antarmuka.
- Menyimpan presisi timestamp harga pasar dan tidak mengarang waktu quote jika provider hanya memberi tanggal sesi.
- Menolak angka non-finite dan snapshot harga yang dimasukkan terlalu jauh ke masa depan.
- Menambah tes API untuk ledger, sumber harga, migrasi database lama, ekspor, dan validasi.
- Menerjemahkan dokumentasi utama ke bahasa Indonesia.

## 0.2.0 — MVP siap dokumentasi portofolio

- Menu target keuangan dibuat generik; tidak ada kategori target yang dikunci.
- Tambah, ubah, dan hapus target.
- Tambah favicon, README, arsitektur, keamanan, panduan kontribusi, serta GitHub Actions.

## 0.1.0 — MVP awal

- Dashboard lokal FastAPI dan SQLite.
- Ledger transaksi dan perhitungan modal/nilai/P&L.
- Snapshot manual harga Tabungan Emas Pegadaian.
- Koneksi quote SPY dan USD/IDR melalui Twelve Data.
- Grafik histori, arus kas, dan target pribadi dasar.
