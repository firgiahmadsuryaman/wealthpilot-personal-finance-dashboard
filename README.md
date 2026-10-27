# WealthPilot — Dasbor Keuangan dan Investasi Pribadi

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-database-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Lisensi MIT](https://img.shields.io/badge/Lisensi-MIT-green.svg)](LICENSE)

**WealthPilot adalah dashboard personal finance dan investasi** untuk memisahkan modal yang disetor, nilai pasar terkini, serta keuntungan atau kerugian. Aplikasi ini dirancang untuk penggunaan pribadi di komputer lokal, khususnya bagi orang dengan pendapatan freelance yang tidak selalu sama setiap bulan.

> **Sumber harga saat ini:** quote emas spot global XAU dalam USD/troy ounce dari [Standard Bullion](https://standardbullion.com/gold-price-api), dengan harga `ask` dan `bid`, lalu dikonversi menjadi estimasi rupiah per gram memakai kurs USD/IDR dari Twelve Data. SPY dan kurs USD/IDR menggunakan Twelve Data jika API key, akses instrumen, dan izin datanya tersedia. Harga emas spot ini **bukan harga resmi Tabungan Emas Pegadaian** dan bukan janji harga transaksi di Indonesia.

## Daftar isi

- [Tujuan proyek](#tujuan-proyek)
- [Fitur utama](#fitur-utama)
- [Cara menghitung portofolio](#cara-menghitung-portofolio)
- [Harga emas spot: harga beli dan jual](#harga-emas-spot-harga-beli-dan-jual)
- [SPY dan kurs USD/IDR](#spy-dan-kurs-usdidr)
- [Teknologi](#teknologi)
- [Instalasi di Windows](#instalasi-di-windows)
- [Pengujian](#pengujian)
- [Endpoint API](#endpoint-api)
- [Pemecahan masalah](#pemecahan-masalah)
- [Keamanan dan privasi](#keamanan-dan-privasi)
- [Pengembangan berikutnya](#pengembangan-berikutnya)
- [Portofolio GitHub dan LinkedIn](#portofolio-github-dan-linkedin)

## Tujuan proyek

WealthPilot membantu pengguna menjawab beberapa pertanyaan dasar: berapa modal bersih yang sudah disetorkan, berapa estimasi nilai aset sekarang, berapa keuntungan atau kerugian, seberapa baru harga yang digunakan, dan bagaimana perkembangan target keuangan yang dibuat sendiri.

Prinsip utamanya:

1. Setoran modal tidak boleh salah dihitung sebagai keuntungan.
2. Harga pasar selalu ditampilkan bersama sumber, timestamp, dan status kesegaran bila tersedia.
3. Pendapatan yang tidak menentu tidak dipaksa menjadi komitmen pembelian bulanan.
4. Target keuangan bersifat bebas, tidak dikunci pada kategori rumah atau pernikahan.
5. Harga yang tidak tersedia tidak boleh diubah menjadi nol atau angka rekaan.
6. Quote pasar digunakan untuk estimasi; transaksi tetap dicatat memakai harga eksekusi sebenarnya.

## Fitur utama

- **Ringkasan portofolio:** modal bersih, kas dalam ledger, nilai pasar, P/L terealisasi, dan P/L belum terealisasi.
- **Ledger transaksi:** setoran, penarikan, saldo awal aset, pembelian, penjualan, biaya, dan dividen dengan validasi kas dan kuantitas.
- **Market Monitor emas:** live dealer quote XAU `ask` dan `bid` dalam USD/troy ounce, estimasi harga beli/jual IDR per gram, perubahan harian dari provider, timestamp, status data, dan atribusi sumber.
- **Grafik emas:** histori spot XAU; harga historis USD/oz dikonversi ke IDR/gram menggunakan kurs USD/IDR terbaru dan diberi keterangan bahwa kurs historis tidak diterapkan.
- **SPY dan USD/IDR:** quote dan grafik candle historis melalui Twelve Data, mengikuti kuota, hak akses, serta lisensi dari akun pengguna.
- **Rentang grafik:** emas 24 jam, 7 hari, 1 bulan, dan 1 tahun; SPY 1 hari, 5 hari, 1 bulan, dan 1 tahun.
- **Kesegaran data:** cache, timestamp, fallback histori lokal yang diberi label basi, dan pesan kegagalan provider.
- **Target keuangan fleksibel:** buat, ubah, dan hapus target dengan nama, nominal, progres, tanggal, serta catatan sendiri.
- **Arus kas dan komposisi aset.**
- **Ekspor transaksi CSV** dan **cadangan JSON** untuk data lokal.
- **Pengujian otomatis** dan GitHub Actions.

## Cara menghitung portofolio

| Istilah | Makna |
|---|---|
| Modal bersih | Setoran eksternal + dasar modal saldo awal aset − penarikan eksternal. Setoran baru bukan keuntungan. |
| Saldo kas portofolio | Kas yang tercatat di ledger setelah setoran, penarikan, pembelian, penjualan, dan dividen. Ini bukan saldo seluruh rekening bank. |
| Nilai portofolio | Saldo kas + estimasi nilai pasar aset yang bisa dinilai. |
| P/L belum terealisasi | Nilai pasar aset yang masih dimiliki − dasar modal aset yang tersisa. |
| P/L terealisasi | Hasil penjualan bersih dibanding dasar modal unit yang dijual, ditambah pendapatan dividen yang dicatat. |
| P/L total | Nilai portofolio − modal bersih, hanya bila valuasi aset lengkap. |

Dasar modal penjualan menggunakan metode rata-rata tertimbang. Biaya transaksi dimasukkan ke dasar modal pembelian atau mengurangi hasil penjualan. Setiap transaksi pembelian atau penjualan sebaiknya menggunakan harga eksekusi yang tercatat pada aplikasi tempat transaksi dilakukan, bukan harga benchmark pasar semata.

## Harga emas spot: harga beli dan jual

WealthPilot memakai feed publik [Standard Bullion Gold Price API](https://standardbullion.com/gold-price-api). Feed memberi dua harga dalam USD per troy ounce:

- **Ask — harga indikatif beli:** harga acuan saat membeli emas dari dealer sumber.
- **Bid — harga indikatif jual:** harga acuan yang dealer sumber bayar saat membeli emas dari pengguna.

Harga IDR per gram dihitung dengan rumus:

```text
harga IDR/gram = harga USD/troy ounce × kurs IDR per USD ÷ 31,1034768
```

Standard Bullion menyebut feed live diperbarui saat pasar aktif dan cache endpoint sekitar 15 detik; rentang histori intraday dipublikasikan pada granularitas 15 menit. WealthPilot meng-cache quote lokal dengan nilai bawaan 30 detik dan melakukan polling dari dashboard setiap 30 detik. Karena itu, fitur ini adalah **pemantauan harga spot mendekati real-time**, bukan streaming tick-by-tick yang dijamin.

**Penting:** angka ini merupakan harga spot/dealer internasional, bukan harga jual/buyback resmi Tabungan Emas Pegadaian atau harga pasti di Pluang. Harga lokal dapat berbeda karena kurs, premi produk, spread, pajak, serta biaya. Harga bid digunakan untuk memperkirakan nilai yang mungkin diterima saat menjual berdasarkan benchmark spot, bukan untuk menjamin jumlah pencairan sebenarnya.

Grafik historis provider hanya memberi seri harga spot USD/oz. Agar dapat digambar dalam rupiah, WealthPilot mengonversi titik historis menggunakan kurs USD/IDR **terkini**; histori harga IDR karenanya merupakan estimasi dan bukan rekonstruksi historis kurs-per-waktu. Jika quote kurs tidak tersedia, sistem tidak menciptakan harga IDR.

Atribusi `Data by Standard Bullion` beserta tautan sumber harus tetap terlihat di antarmuka. Endpoint publik emas tidak membutuhkan API key menurut dokumentasi penyedia, tetapi aturan akses, batas permintaan, dan persyaratan atribusi tetap perlu dihormati. API ini digunakan sebagai sumber harga pasar, bukan integrasi akun pribadi.

## SPY dan kurs USD/IDR

Buat file `.env` dari `.env.example`, lalu isi API key Twelve Data milikmu:

```dotenv
TWELVE_DATA_API_KEY=masukkan_api_key_milikmu
SPY_CACHE_SECONDS=60
USDIDR_CACHE_SECONDS=900
SPY_QUOTE_INTERVAL=1min
USDIDR_QUOTE_INTERVAL=1min
SPY_SERIES_CACHE_SECONDS=60
GOLD_CACHE_SECONDS=30
GOLD_SERIES_CACHE_SECONDS=60
```

WealthPilot memakai endpoint [`/quote`](https://twelvedata.com/docs#quote) dan [`/time_series`](https://twelvedata.com/docs#time-series). Grafik SPY tersedia melalui `/api/market/series/SPY?range=1D` dengan rentang `1D`, `5D`, `1M`, dan `1Y`. Quote USD/IDR juga dipakai untuk mengonversi harga emas spot serta nilai SPY ke rupiah.

Harga SPY real-time/tertunda, akses instrumen, jumlah permintaan, dan hak tampilan bergantung pada paket serta lisensi API key. WealthPilot menggunakan polling dan cache, bukan streaming tick-by-tick. Nilai SPY dalam IDR adalah estimasi berdasarkan quote SPY dan USD/IDR, bukan nilai eksekusi aktual dari Pluang.

## Teknologi

- **Backend:** Python 3.10+, FastAPI, Pydantic, HTTPX
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript
- **Data emas:** Standard Bullion public spot quote dan histori XAU
- **Data SPY/FX:** Twelve Data
- **Pengujian:** `unittest`, FastAPI `TestClient`
- **CI:** GitHub Actions

## Instalasi di Windows

### Cara mudah

1. Pasang Python 3.10 atau yang lebih baru.
2. Ekstrak proyek atau clone repository.
3. Buka folder proyek di File Explorer.
4. Jalankan `run.bat`.
5. Buka [http://127.0.0.1:8000](http://127.0.0.1:8000).
6. Isi `TWELVE_DATA_API_KEY` di `.env` agar SPY dan konversi USD/IDR tersedia; hentikan dan jalankan ulang server sesudah mengubah `.env`.
7. Harga emas spot dapat diminta dari Standard Bullion tanpa API key khusus emas. Konversi IDR/gram tetap memerlukan quote USD/IDR yang valid dari Twelve Data.
8. Masukkan saldo awal atau transaksi aktual sebelum menggunakan ringkasan untuk menilai portofolio pribadi.

Jika `.env` sudah ada, jangan menimpanya karena bisa berisi API key milikmu.

### Instalasi manual melalui PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Jika PowerShell melarang aktivasi virtual environment, periksa kebijakan eksekusi di komputermu atau jalankan Python dari `.venv`. Hentikan server dengan `Ctrl+C`.

## Pengujian

```powershell
python -m unittest discover -s tests -v
node --check app/static/app.js
python -m py_compile app/main.py
```

Tes memakai data dan database sementara; tes tidak mengisi aset contoh ke database pribadimu. Jalankan pengujian sebelum membuat commit.

## Endpoint API

Dokumentasi interaktif FastAPI tersedia di [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) ketika aplikasi berjalan.

| Endpoint | Fungsi |
|---|---|
| `GET /api/health` | Status aplikasi dan konfigurasi sumber data |
| `GET /api/overview` | Ringkasan portofolio, harga, target, dan transaksi terbaru |
| `GET /api/market` | Quote XAU bid/ask, quote SPY, kurs USD/IDR, dan status provider |
| `GET /api/market/gold/series?range=1D` | Histori emas spot XAU dikonversi ke IDR/gram; rentang `1D`, `5D`, `1M`, `1Y` |
| `GET /api/market/series/SPY?range=1D` | Candle historis SPY dari Twelve Data |
| `GET /api/market/history/{symbol}` | Snapshot tersimpan untuk SPY atau USD/IDR |
| `GET /api/market/pegadaian/history` | Histori manual lama, jika data Pegadaian pernah dicatat; tidak digunakan sebagai live feed utama |
| `POST /api/market/pegadaian` | Endpoint kompatibilitas untuk menyimpan snapshot manual lama; tidak dipakai Market Monitor spot |
| `GET /api/transactions` | Daftar transaksi |
| `POST /api/transactions` | Validasi dan catat transaksi |
| `PUT /api/transactions/{id}` | Ubah transaksi dan validasi ulang ledger |
| `DELETE /api/transactions/{id}` | Hapus transaksi jika sisa ledger tetap valid |
| `GET /api/export/transactions.csv` | Unduh transaksi sebagai CSV |
| `GET /api/export/backup.json` | Unduh cadangan tabel lokal sebagai JSON |
| `GET /api/goals` | Daftar target keuangan |
| `POST /api/goals` | Buat target |
| `PUT /api/goals/{id}` | Ubah target |
| `DELETE /api/goals/{id}` | Hapus target |

## Pemecahan masalah Market Monitor

1. **Periksa konfigurasi:** buka `http://127.0.0.1:8000/api/health`. `twelve_data_configured` harus `true` untuk SPY dan konversi USD/IDR. Feed emas spot tidak memerlukan API key terpisah.
2. **Periksa quote:** buka `http://127.0.0.1:8000/api/market`. Lihat status, pesan, harga, dan timestamp untuk `gold`, `spy`, dan `fx`.
3. **Periksa grafik emas:** buka `http://127.0.0.1:8000/api/market/gold/series?range=1D&force=true`. Respons sukses berisi `status: "ok"`, `item_count`, dan `items`. Jika FX tidak tersedia, harga IDR/gram tidak dibuat-buat.
4. **Periksa grafik SPY:** buka `http://127.0.0.1:8000/api/market/series/SPY?range=1D&force=true`. Respons sukses memuat `items` berisi timestamp dan harga candle. Error bisa disebabkan API key, kuota, paket, izin simbol, atau jaringan.
5. **Harga berubah lambat:** harga spot diperbarui ketika pasar emas internasional aktif; saat pasar tutup, timestamp quote terakhir dapat tetap sama. Grafik historis intraday memiliki granularitas 15 menit, tidak setiap detik.
6. **Quote basi:** jika provider gagal, histori lokal bisa ditampilkan dengan status `stale`. Periksa pesan provider dan timestamp sebelum menganggapnya sebagai harga terbaru.
7. **Browser masih menampilkan file lama:** tekan `Ctrl+F5` untuk memuat ulang CSS dan JavaScript.

Jangan membagikan API key atau file `.env`. Saat meminta bantuan, kirim pesan error yang sudah dibersihkan dari rahasia.

## Pencadangan

Di menu **Pengaturan data**, gunakan **Cadangkan seluruh data** untuk mengunduh JSON berisi transaksi, target, snapshot pasar, candle SPY, dan tabel snapshot Pegadaian manual lama jika ada. File cadangan merupakan data keuangan pribadi; simpan aman dan jangan masukkan ke repository publik. Fitur ekspor tersedia, sedangkan impor/pemulihan otomatis belum tersedia.

## Keamanan dan privasi

- Aplikasi secara default mendengarkan `127.0.0.1` di komputer lokal.
- Jangan mengunggah `.env`, database SQLite, catatan transaksi, log, file cadangan, atau tangkapan layar yang menampilkan saldo pribadi.
- Jangan memasukkan password, PIN, OTP, cookie, atau token sesi Pegadaian/Pluang.
- Jangan mengekspos server ke internet/LAN tanpa autentikasi, HTTPS, pembatasan akses, backup, dan peninjauan keamanan.
- API key Twelve Data hanya disimpan di `.env`, bukan di HTML atau JavaScript.
- Harga dan data pihak ketiga tetap tunduk pada batas serta lisensi penyedianya; atribusi Standard Bullion harus dipertahankan.

Lihat [SECURITY.md](SECURITY.md).

## Pengembangan berikutnya

- [x] Pisahkan modal bersih dari nilai pasar dan P/L.
- [x] Validasi saldo kas dan kuantitas transaksi.
- [x] Quote emas spot bid/ask dan harga estimasi IDR/gram.
- [x] Grafik histori XAU dan SPY dengan timestamp serta status data.
- [x] Quote SPY/USD/IDR dengan cache dan fallback data basi yang diberi label.
- [x] CRUD target keuangan bebas.
- [x] Ekspor ledger CSV dan cadangan JSON.
- [x] Tes otomatis untuk alur inti dan sumber data.
- [ ] Impor CSV dengan pemeriksaan dan pratinjau rekonsiliasi.
- [ ] Jejak audit untuk koreksi transaksi.
- [ ] Autentikasi bila kelak dikembangkan menjadi versi hosting multi-pengguna.
- [ ] Pengujian koneksi harga pasar end-to-end secara berkala dengan API key dan jaringan pengguna.

## Portofolio GitHub dan LinkedIn

Panduan repository, riwayat commit berbahasa Indonesia, serta deskripsi proyek untuk LinkedIn ada di [docs/PANDUAN_GITHUB_LINKEDIN_ID.md](docs/PANDUAN_GITHUB_LINKEDIN_ID.md) dan [docs/PORTFOLIO_GUIDE_ID.md](docs/PORTFOLIO_GUIDE_ID.md).

## Lisensi

Proyek ini menggunakan [MIT License](LICENSE). Lisensi proyek tidak memberikan hak untuk mendistribusikan ulang data pasar pihak ketiga.
