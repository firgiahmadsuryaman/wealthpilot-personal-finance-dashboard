# Catatan Perubahan

## [0.4.1] - 2026-10-28

### Diperbaiki
- Market Monitor menampilkan perubahan persentase sepanjang rentang grafik serta close candle terakhir dan waktu candle.
- Pesan kegagalan sumber data tetap terlihat meskipun histori lama masih dapat digambar.
- Permintaan candle memakai parameter urutan `asc` sesuai dokumentasi Twelve Data.
- Cache candle bawaan diubah menjadi 60 detik dan aset statis diberi versi untuk mengurangi masalah cache browser.
- Dokumentasi menambahkan endpoint pemeriksaan Market Monitor serta langkah diagnosis status API.

### Batasan yang diketahui
- Data langsung tetap mensyaratkan API key Twelve Data dan hak akses data yang sesuai.
- Grafik harga Pegadaian hanya mengandung snapshot yang benar-benar disimpan dari harga di Tring!; tidak ada integrasi akun otomatis.

## [0.4.0] - 2026-10-28

### Ditambahkan
- Grafik SPY mengambil candle historis dari endpoint `time_series` Twelve Data, tidak lagi bergantung hanya pada snapshot lokal quote.
- Pilihan rentang grafik 1D, 5D, 1M, dan 1Y dengan interval candle yang sesuai.
- Penyimpanan candle historis ke SQLite melalui tabel `market_bars`, termasuk fallback dengan label data basi ketika provider gagal.
- Interval quote 1 menit yang dapat dikonfigurasi untuk SPY dan USD/IDR.
- Refresh manual yang melewati cache quote/grafik serta indikator status jumlah candle, interval, dan status cache.
- Pengujian untuk candle provider, pengurutan waktu, persistensi, fallback stale, dan keadaan tanpa API key.

### Diperbaiki
- Market Monitor kini meminta histori harga provider agar grafik dapat muncul sejak pertama kali digunakan saat API memiliki izin dan data tersedia.
- Ekspor cadangan menyesuaikan tabel candle yang menggunakan primary key gabungan.
- Waktu dan status grafik membedakan histori provider dari snapshot yang sudah tersimpan.

### Batasan yang diketahui
- Status respons provider yang berhasil bukan jaminan bahwa paket API menyediakan data real-time; keterlambatan mengikuti paket/lisensi.
- Harga Tabungan Emas Pegadaian tetap dimasukkan dari aplikasi Tring! untuk menjaga kesesuaian dengan harga produk pengguna.

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
