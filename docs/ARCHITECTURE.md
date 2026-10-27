# Arsitektur Teknis WealthPilot

## Diagram konteks

```text
Browser (HTML, CSS, JavaScript)
               |
               | JSON same-origin
               v
       FastAPI (app/main.py)
          |      |      |
          |      |      +---- Twelve Data API (quote SPY dan USD/IDR)
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
| `GET /api/market/history/{symbol}` | Histori SPY atau USD/IDR |
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

## Strategi quote

1. Jika API key belum diisi, API menandai sumber sebagai belum dikonfigurasi.
2. Quote diambil dari endpoint quote Twelve Data dan di-cache sesuai TTL pada `.env`.
3. `last_quote_at` digunakan sebagai waktu quote bila disediakan. Bila provider hanya mengirim tanggal sesi atau timestamp candle, presisinya diberi label dan tidak dipresentasikan sebagai waktu quote yang tepat.
4. Snapshot harga disimpan agar grafik histori terbentuk dari data yang benar-benar diterima.
5. Jika provider gagal, quote cache/database dapat dipakai sebagai data basi dan diberi status `stale`; aplikasi tidak membuat harga baru.
6. Harga emas hanya berubah di dashboard setelah pengguna menyimpan snapshot yang disalin dari Tring!.
7. Snapshot Pegadaian yang berusia lebih dari 24 jam ditandai basi; sumber harga tidak dipalsukan saat provider tidak tersedia.

## Batasan arsitektur

- Mode saat ini lokal dan satu pengguna; tidak ada login, role, atau penyimpanan multi-pengguna.
- Quote memakai polling dan cache, bukan streaming tick-by-tick.
- Snapshot harga emas manual bukan integrasi otomatis Pegadaian.
- SQLite sesuai untuk aplikasi desktop/pribadi ringan, tetapi bukan pilihan final untuk server publik multi-pengguna.
- Untuk hosting diperlukan autentikasi/otorisasi, HTTPS, backup, observability, rate limiting, manajemen rahasia, lisensi data, dan security review.
