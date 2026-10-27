# Arsitektur Teknis WealthPilot

## Diagram konteks

```text
Browser (HTML, CSS, JavaScript)
               |
               | JSON same-origin
               v
       FastAPI (app/main.py)
          |       |       |
          |       |       +---- Standard Bullion API (harga XAU ask/bid dan histori)
          |       |
          |       +------------ Twelve Data API (quote SPY dan kurs USD/IDR)
          |
          +-------------------- SQLite (ledger, target, snapshot dan candle)
```

## Komponen

- `app/static/`: HTML, CSS, dan JavaScript untuk antarmuka.
- `app/main.py`: validasi request, API, akses SQLite, cache quote, konektor provider, aturan ledger, dan perhitungan portofolio.
- `data/wealthpilot.db`: database lokal yang dibuat otomatis; tidak boleh masuk version control.
- `.env`: konfigurasi rahasia lokal, terutama API key Twelve Data dan TTL cache.
- `tests/`: tes unit/API yang menggunakan database sementara dan respons provider tiruan.
- `.github/workflows/tests.yml`: menjalankan tes saat push atau pull request.

## Aturan database

- `transactions`: ledger transaksi dan harga eksekusi yang dicatat pengguna.
- `goals`: target keuangan buatan pengguna.
- `market_snapshots`: snapshot quote SPY, USD/IDR, dan XAU ask/bid yang pernah diterima.
- `market_bars`: candle historis SPY yang disimpan untuk fallback bila provider tidak tersedia.
- `pegadaian_rates`: tabel kompatibilitas untuk snapshot Pegadaian manual dari versi lama; tidak menjadi sumber harga langsung Market Monitor versi terbaru.

Akses database menggunakan koneksi singkat yang selalu ditutup. Insert transaksi divalidasi terhadap ledger secara kronologis sebelum commit; request jaringan ke provider tidak dilakukan saat transaksi tulis SQLite sedang berjalan.

## Endpoint inti

| Endpoint | Kegunaan |
|---|---|
| `GET /api/health` | Status aplikasi, API key Twelve Data, dan provider emas |
| `GET /api/overview` | Ringkasan portofolio, harga, target, transaksi terakhir |
| `GET /api/market` | Quote XAU ask/bid, SPY, USD/IDR, timestamp, status sumber |
| `GET /api/market/gold/series?range=1D` | Histori spot emas dikonversi ke IDR/gram |
| `GET /api/market/series/SPY?range=1D` | Candle historis SPY dari Twelve Data |
| `GET /api/market/history/{symbol}` | Snapshot SPY atau USD/IDR yang tersimpan |
| `GET /api/market/pegadaian/history` | Data snapshot Pegadaian manual lama jika masih ada |
| `POST /api/market/pegadaian` | Endpoint kompatibilitas untuk menyimpan snapshot manual lama; tidak digunakan UI utama |
| `GET /api/transactions` | Daftar transaksi |
| `POST /api/transactions` | Catat transaksi tervalidasi |
| `PUT /api/transactions/{id}` | Ubah transaksi dengan validasi ulang ledger |
| `DELETE /api/transactions/{id}` | Hapus transaksi jika ledger tersisa tetap valid |
| `GET /api/export/transactions.csv` | Ekspor ledger |
| `GET /api/export/backup.json` | Ekspor tabel data lokal |
| `GET /api/goals` | Daftar target keuangan |
| `POST /api/goals` | Buat target |
| `PUT /api/goals/{id}` | Ubah target |
| `DELETE /api/goals/{id}` | Hapus target |

Dokumentasi interaktif tersedia di `/docs` selama aplikasi berjalan.

## Strategi harga spot emas

1. `GET https://standardbullion.com/spot-prices.json` mengambil XAU `ask`, `bid`, `updated`, `changeToday`, serta `attribution` dalam USD/troy ounce.
2. `ask` merupakan harga indikatif untuk membeli dari dealer sumber; `bid` merupakan harga indikatif yang dibayar dealer sumber ketika membeli kembali.
3. `USD/IDR` diambil dari Twelve Data, lalu harga dikonversi dengan rumus `USD/oz × IDR per USD ÷ 31.1034768`.
4. Harga IDR/gram hanya dihitung jika quote USD/IDR valid. Sistem tidak menebak kurs ketika data FX tidak tersedia.
5. Feed quote emas di-cache di backend sesuai `GOLD_CACHE_SECONDS` (default 30 detik); feed penyedia memiliki cache tersendiri. Refresh dan polling tidak menjamin setiap perubahan tick dapat diterima.
6. Histori XAU didapatkan dari endpoint market history Standard Bullion. Titik historis USD/oz dikonversi memakai kurs terkini dan antarmuka menyatakan batasan tersebut.
7. Snapshot lokal disimpan untuk observabilitas/fallback. Ketika provider gagal, histori lokal diberi status `stale`; harga stale tidak dilabeli sebagai data terbaru.
8. UI mempertahankan atribusi `Data by Standard Bullion` beserta tautan sumber.

**Batas harga:** quote merupakan benchmark dealer spot global, bukan harga beli/jual resmi Tabungan Emas Pegadaian, bukan harga eksekusi Pluang, dan bukan penawaran transaksi di Indonesia. Premi, spread lokal, jenis produk, pajak, dan biaya dapat membuat harga akhir berbeda. Nilai portofolio emas menggunakan bid spot IDR/gram sebagai estimasi nilai jual, bukan jaminan hasil pencairan.

## Strategi SPY dan FX

1. Quote SPY dan USD/IDR menggunakan endpoint quote Twelve Data dengan cache yang dapat dikonfigurasi.
2. Grafik SPY menggunakan `time_series`, menyimpan candle yang diterima, dan menandai fallback database sebagai stale.
3. Timestamp quote/candle dipertahankan dari provider bila tersedia; aplikasi tidak mengubah tanggal sesi menjadi waktu quote yang presisi.
4. Akses instrumen, delay, rate limit, serta izin tampilan mengikuti paket dan lisensi API key yang digunakan.
5. Refresh grafik emas tidak memaksa quote FX baru pada setiap pergantian rentang; tombol refresh pasar memperbarui quote FX sebelum histori dimuat kembali.

## Batasan arsitektur

- Versi ini lokal dan satu pengguna; tidak ada login, role, atau penyimpanan multi-pengguna.
- Quote menggunakan polling dan cache, bukan streaming tick-by-tick yang dijamin.
- Feed emas tidak membaca saldo maupun harga transaksi personal dari Pegadaian atau Pluang.
- Riwayat IDR emas adalah estimasi yang dikonversi dengan kurs saat ini, bukan histori lengkap harga emas lokal.
- SQLite sesuai untuk aplikasi pribadi lokal, bukan pilihan final untuk server publik multi-pengguna.
- Hosting publik memerlukan autentikasi/otorisasi, HTTPS, backup, observability, rate limiting, manajemen rahasia, lisensi data, serta security review.
