# Arsitektur Teknis WealthPilot

## Diagram konteks

```text
Browser (HTML, CSS, JavaScript)
               |
               | JSON same-origin
               v
       FastAPI (app/main.py)
          |      |      |
          |      |      +---- Twelve Data API (quote intraday + candle time_series SPY)
          |      |
          |      +----------- Input snapshot harga Tring! oleh pengguna
          |
          +----------------- SQLite (transaksi, tujuan, histori harga)
```

## Komponen

- `app/static/`: HTML, CSS, dan JavaScript untuk antarmuka dashboard.
- `app/main.py`: validasi request, API, akses SQLite, quote provider, aturan ledger, dan perhitungan portofolio.
- `data/wealthpilot.db`: database lokal yang dibuat otomatis saat aplikasi mulai; tidak boleh masuk version control.
- `.env`: konfigurasi rahasia lokal untuk API key dan interval cache.
- `tests/`: tes unit dan API yang menggunakan database sementara.
- `.github/workflows/tests.yml`: menjalankan tes secara otomatis saat push atau pull request.

## Aturan database

Tabel utama:

- `transactions`: ledger transaksi dan nilai eksekusi yang dicatat pengguna.
- `pegadaian_rates`: snapshot harga beli/jual kembali Pegadaian, unit mentah dan nilai normalisasi, sumber, catatan, serta waktu.
- `market_snapshots`: quote SPY atau USD/IDR yang pernah diperoleh dari provider.
- `goals`: target keuangan yang bisa dibuat pengguna.

Akses database menggunakan koneksi pendek yang selalu di-commit, di-rollback saat error, dan ditutup setelah dipakai. Insert transaksi divalidasi secara kronologis sebelum commit; request eksternal provider dilakukan sesudah transaksi database selesai agar tidak menahan kunci tulis SQLite.

## Endpoint inti

| Endpoint | Kegunaan |
|---|---|
| `GET /api/health` | Status aplikasi dan konfigurasi data |
| `GET /api/overview` | Portofolio, market, target, transaksi terbaru |
| `GET /api/market` | Quote SPY, kurs, harga Pegadaian terakhir |
| `POST /api/market/pegadaian` | Simpan snapshot harga manual |
| `GET /api/market/pegadaian/history` | Histori snapshot Pegadaian |
| `GET /api/market/history/{symbol}` | Histori quote SPY atau USD/IDR |
| `GET /api/market/series/SPY?range=1D` | Candle historis dari Twelve Data untuk grafik; rentang 1D/5D/1M/1Y |
| `GET /api/transactions` | Daftar ledger |
| `POST /api/transactions` | Catat transaksi tervalidasi |
| `PUT /api/transactions/{id}` | Ubah transaksi dan validasi ulang seluruh ledger |
| `DELETE /api/transactions/{id}` | Hapus transaksi hanya jika ledger yang tersisa masih valid |
| `GET /api/export/transactions.csv` | Ekspor ledger untuk backup/analisis |
| `GET /api/export/backup.json` | Ekspor seluruh tabel data lokal sebagai JSON |
| `GET /api/goals` | Daftar target |
| `POST /api/goals` | Buat target |
| `PUT /api/goals/{id}` | Perbarui target |
| `DELETE /api/goals/{id}` | Hapus target |

Dokumentasi OpenAPI interaktif dapat dibuka dari `/docs` ketika aplikasi sedang berjalan.

## Strategi quote dan grafik historis

1. Jika API key belum diisi, API menandai sumber sebagai belum dikonfigurasi dan tidak mengarang harga.
2. Quote SPY dan USD/IDR diambil dari endpoint `/quote` Twelve Data dengan interval konfigurasi dan di-cache sesuai TTL pada `.env`.
3. Grafik SPY meminta candle OHLCV melalui endpoint `/time_series`. Rentang 1D memakai interval 1 menit (hingga 390 candle), 5D memakai interval 5 menit (hingga 390 candle), 1M memakai interval harian (30 candle), dan 1Y memakai interval harian (252 candle).
4. Candle diurutkan berdasarkan waktu provider, disimpan ke tabel `market_bars`, dan ditampilkan dengan label sumber, jumlah candle, perubahan dalam rentang terpilih, close candle terakhir, serta waktu candle.
5. Cache grafik bawaan 60 detik menyeimbangkan pembaruan dan penggunaan kuota. Refresh manual melewati cache aplikasi untuk meminta respons baru dari provider. Cache provider eksternal dan keterlambatan paket tetap berada di luar kendali WealthPilot.
6. Jika provider gagal, histori database dapat ditampilkan dengan status `stale` dan keterangan kegagalan; bila belum ada data tersimpan, respons menjelaskan bahwa data belum dikonfigurasi atau tidak tersedia.
7. `last_quote_at` dipakai sebagai waktu quote bila tersedia. Bila provider hanya mengirim tanggal sesi atau timestamp candle, presisinya diberi label dan tidak dipresentasikan sebagai waktu quote yang tepat.
8. Grafik emas menggunakan snapshot harga jual kembali yang dimasukkan berdasarkan Tring!; tidak ada penggantian otomatis dengan harga spot global. Grafik memerlukan sedikitnya dua snapshot untuk menunjukkan perubahan.
9. Snapshot Pegadaian yang berusia lebih dari 24 jam ditandai basi. Status “berhasil dari provider” tidak dimaknai sebagai jaminan data tick-by-tick.

## Batasan arsitektur

- Mode saat ini lokal dan satu pengguna; tidak ada login, role, atau penyimpanan multi-pengguna.
- Quote memakai polling dan cache, bukan streaming tick-by-tick.
- Snapshot harga emas manual bukan integrasi otomatis Pegadaian.
- SQLite sesuai untuk aplikasi desktop/pribadi ringan, tetapi bukan pilihan final untuk server publik multi-pengguna.
- Untuk hosting diperlukan autentikasi/otorisasi, HTTPS, backup, observability, rate limiting, manajemen rahasia, lisensi data, dan security review.
