# WealthPilot — Dasbor Keuangan dan Investasi Pribadi

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-database-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Lisensi MIT](https://img.shields.io/badge/Lisensi-MIT-green.svg)](LICENSE)

**WealthPilot adalah proyek portofolio personal finance dashboard yang membantu pengguna memisahkan modal asli, nilai pasar, dan keuntungan/kerugian investasi.** Aplikasi dirancang untuk penggunaan pribadi di komputer lokal, terutama untuk orang dengan pendapatan yang tidak selalu sama setiap bulan.

> **Status sumber data:** harga Tabungan Emas Pegadaian diinput dari informasi aktual yang terlihat pada aplikasi Tring! by Pegadaian. Harga SPY dan kurs USD/IDR diambil dari Twelve Data jika API key, akses instrumen, serta izin penggunaan data tersedia. Aplikasi ini belum terhubung langsung ke akun Pegadaian maupun Pluang dan bukan aplikasi trading.

## Daftar isi

- [Tujuan proyek](#tujuan-proyek)
- [Fitur](#fitur)
- [Cara perhitungan](#cara-perhitungan)
- [Sumber dan kesegaran data](#sumber-dan-kesegaran-data)
- [Teknologi](#teknologi)
- [Instalasi di Windows](#instalasi-di-windows)
- [Menjalankan pengujian](#menjalankan-pengujian)
- [API yang tersedia](#api-yang-tersedia)
- [Keamanan dan privasi](#keamanan-dan-privasi)
- [Rencana pengembangan](#rencana-pengembangan)
- [Portofolio GitHub dan LinkedIn](#portofolio-github-dan-linkedin)

## Tujuan proyek

WealthPilot dikembangkan untuk menyelesaikan masalah pencatatan keuangan yang umum terjadi:

1. Modal yang disetorkan sering tercampur dengan kenaikan atau penurunan harga aset.
2. Harga pasar tidak berguna jika sumber dan waktu pembaruannya tidak jelas.
3. Pendapatan freelance yang tidak menentu membutuhkan alokasi yang fleksibel, bukan kewajiban investasi bulanan.
4. Pengguna perlu membuat target keuangan sendiri tanpa menu tetap seperti rumah atau pernikahan.
5. Harga yang tidak tersedia tidak boleh dianggap nol karena akan menghasilkan valuasi yang menyesatkan.

## Fitur

- **Ringkasan portofolio:** modal bersih, nilai portofolio, kas, P/L total, P/L terealisasi, dan P/L belum terealisasi.
- **Ledger transaksi:** setoran, penarikan, saldo awal aset, pembelian, penjualan, biaya, dividen/pendapatan kas, serta koreksi transaksi dengan validasi ulang urutan ledger.
- **Tabungan Emas Pegadaian:** simpan harga beli nasabah dan harga jual kembali dari Tring!, satuan harga, sumber, catatan, timestamp, serta histori snapshot.
- **SPY dan USD/IDR:** quote melalui Twelve Data ketika API dan paket data mengizinkan.
- **Persentase kenaikan/penurunan:** SPY memakai perubahan yang diberikan provider; emas membandingkan snapshot Pegadaian terbaru dengan snapshot sebelumnya yang dicatat.
- **Status data:** harga baru, tersimpan dari database, belum dikonfigurasi, atau tidak tersedia ditangani secara terpisah.
- **Grafik histori:** dibangun dari snapshot yang benar-benar tersimpan, bukan data contoh.
- **Target keuangan fleksibel:** pengguna dapat membuat, mengubah, dan menghapus target dengan nama, nominal, progres awal, catatan, dan tanggal target sendiri.
- **Arus kas dan komposisi portofolio.**
- **Ekspor riwayat transaksi ke CSV** untuk analisis spreadsheet, serta **cadangan JSON seluruh data lokal** (transaksi, target, snapshot Pegadaian, dan histori pasar).
- **Pengujian otomatis** untuk perhitungan, validasi transaksi, harga pasar, target, dan ekspor.
- **GitHub Actions** untuk menjalankan tes pada beberapa versi Python.

## Cara perhitungan

### Istilah utama

| Istilah | Makna |
|---|---|
| Modal bersih | Setoran eksternal + dasar modal saldo awal aset − penarikan eksternal. Setoran baru tidak dicatat sebagai keuntungan. |
| Saldo kas portofolio | Kas yang tercatat di ledger setelah pembelian, penjualan, dividen, setoran, dan penarikan. Ini bukan saldo semua rekening bank pengguna. |
| Nilai portofolio | Kas portofolio + estimasi nilai pasar semua aset yang bisa dinilai. |
| P/L belum terealisasi | Nilai pasar aset yang masih dimiliki − dasar modal aset yang tersisa. |
| P/L terealisasi | Hasil penjualan bersih dibandingkan dasar modal unit yang dijual, ditambah pendapatan dividen yang dicatat. |
| P/L total | Nilai portofolio − modal bersih, ketika valuasi semua kepemilikan lengkap. |

Dasar modal penjualan menggunakan metode rata-rata tertimbang. Biaya transaksi masuk ke dasar modal pembelian atau mengurangi hasil penjualan. Untuk emas, valuasi menggunakan harga jual kembali Pegadaian karena itulah harga yang lebih relevan untuk memperkirakan penerimaan jika saldo dijual kembali.

### Contoh satuan harga emas

Jika Tring! menampilkan harga per 0,01 gram, masukkan satuan **per 0,01 gram** pada formulir harga. Sistem menyimpan harga yang dinormalisasi ke rupiah per gram untuk perhitungan, sekaligus mempertahankan angka mentah yang dimasukkan. Kuantitas aset emas di ledger dicatat dalam gram.

## Sumber dan kesegaran data

### Tabungan Emas Pegadaian / Tring!

Versi ini tidak melakukan login otomatis atau membaca saldo dari akun pribadi. Salin harga beli dan harga jual kembali yang benar-benar terlihat pada Tring!, pilih satuan yang benar, lalu simpan waktu pengamatan. Persentase perubahannya adalah selisih antara snapshot yang berurutan, **bukan jaminan perubahan harian real-time**. Untuk menghindari penyamaan produk, jangan mengganti harga Tabungan Emas Pegadaian dengan harga spot emas internasional atau harga emas fisik produk lain.

Referensi publik Pegadaian: [informasi harga emas](https://pegadaian.co.id/harga-emas) dan [layanan Tabungan Emas](https://pegadaian.co.id/emas/tabungan-emas). Harga yang ditampilkan akun/aplikasi bisa memiliki konteks produk dan ketentuan tersendiri.

### SPY dan USD/IDR

Tambahkan API key pribadi pada file `.env` (interval cache SPY bawaan 60 detik, FX 900 detik; sesuaikan dengan kuota paketmu):

```dotenv
TWELVE_DATA_API_KEY=masukkan_api_key_milikmu
SPY_CACHE_SECONDS=60
USDIDR_CACHE_SECONDS=900
```

Endpoint quote resmi: [Dokumentasi Twelve Data](https://twelvedata.com/docs). Provider menampilkan harga quote, perubahan, persentase perubahan, dan timestamp quote terakhir. Waktu yang tersedia, interval pembaruan, dan apakah datanya real-time atau tertunda bergantung pada paket, lisensi, bursa, serta izin penggunaan data milik pengguna API. WealthPilot melakukan polling dan cache; **ini bukan streaming tick-by-tick**. Jika provider gagal, aplikasi bisa menampilkan snapshot sebelumnya dengan label bahwa datanya basi.

Nilai SPY dalam IDR merupakan estimasi harga SPY dalam USD dikalikan quote USD/IDR. Nilai itu bisa berbeda dari harga eksekusi dan kurs transaksi Pluang, biaya, spread, pajak, serta konversi aktual.

## Teknologi

- **Backend:** Python, FastAPI, Pydantic, HTTPX
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript
- **Data pasar:** Twelve Data untuk SPY dan USD/IDR; snapshot harga Pegadaian dimasukkan manual
- **Pengujian:** `unittest`, `TestClient` FastAPI
- **CI:** GitHub Actions

## Instalasi di Windows

### Cara mudah

1. Pasang Python 3.10 atau yang lebih baru.
2. Ekstrak proyek atau clone repository.
3. Buka folder `wealthpilot` di File Explorer.
4. Jalankan `run.bat`.
5. Buka [http://127.0.0.1:8000](http://127.0.0.1:8000).
6. Untuk harga SPY dan USD/IDR, isi `TWELVE_DATA_API_KEY` di file `.env`, lalu tutup dan jalankan ulang aplikasi.
7. Pada menu **Pengaturan data**, salin harga beli serta harga jual kembali dari Tring! by Pegadaian.
8. Catat saldo awal atau transaksi aktual sebelum menggunakan angka untuk memahami kondisi portofolio pribadi.

Jika `.env` sudah ada, jangan timpa file tersebut karena mungkin sudah berisi API key.

### Instalasi manual melalui PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Jika PowerShell melarang aktivasi virtual environment, pelajari kebijakan eksekusi pada komputer sendiri atau jalankan perintah Python secara langsung dari `.venv`. Hentikan server dengan `Ctrl+C`.

## Menjalankan pengujian

```powershell
python -m unittest discover -s tests -v
```

Tes menggunakan data sintetis di database sementara; tes tidak mengisi aset contoh ke database pribadi WealthPilot. Saat ada perubahan, jalankan tes sebelum commit dan pastikan `git status` tidak menampilkan `.env` atau database lokal.

## API yang tersedia

Dokumentasi interaktif FastAPI tersedia saat server berjalan: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

| Endpoint | Fungsi |
|---|---|
| `GET /api/health` | Status aplikasi dan konfigurasi sumber data |
| `GET /api/overview` | Ringkasan portofolio, harga, target, dan transaksi terakhir |
| `GET /api/market` | Snapshot harga dan status provider |
| `POST /api/market/pegadaian` | Simpan harga beli/jual kembali Pegadaian yang diinput pengguna |
| `GET /api/market/pegadaian/history` | Histori harga Pegadaian yang direkam |
| `GET /api/market/history/{symbol}` | Histori SPY atau USD/IDR yang disimpan |
| `GET /api/transactions` | Daftar transaksi |
| `POST /api/transactions` | Validasi dan catat transaksi |
| `PUT /api/transactions/{id}` | Ubah transaksi dan validasi ulang seluruh ledger |
| `DELETE /api/transactions/{id}` | Hapus transaksi jika sisa ledger tetap valid |
| `GET /api/export/transactions.csv` | Unduh transaksi sebagai CSV |
| `GET /api/export/backup.json` | Unduh cadangan seluruh tabel aplikasi dalam JSON |
| `GET /api/goals` | Daftar target keuangan |
| `POST /api/goals` | Buat target |
| `PUT /api/goals/{id}` | Ubah target |
| `DELETE /api/goals/{id}` | Hapus target |

## Pencadangan

Di menu **Pengaturan data**, pilih **Cadangkan seluruh data** untuk mengunduh JSON berisi tabel transaksi, target keuangan, snapshot harga Pegadaian, dan snapshot market-data. Endpoint ini tidak menyertakan `.env` atau API key. Berkas cadangan tetap merupakan data keuangan pribadi, sehingga simpan secara aman dan jangan masukkan ke repository publik. Fitur ini adalah ekspor; proses impor/pemulihan otomatis belum tersedia.

## Keamanan dan privasi

- Aplikasi secara default hanya mendengarkan `127.0.0.1` di komputer lokal.
- File `.env`, database SQLite, log, riwayat transaksi, berkas cadangan JSON, dan tangkapan layar pribadi tidak boleh diunggah ke GitHub.
- Jangan memasukkan password, PIN, OTP, cookie, atau token sesi Pegadaian/Pluang ke aplikasi.
- Jangan mengekspos server ke internet atau LAN tanpa autentikasi, otorisasi, HTTPS, backup, pembatasan akses, dan peninjauan keamanan.
- API key Twelve Data disimpan di `.env`, bukan di JavaScript atau HTML.
- Data market pihak ketiga memiliki aturan lisensi; jangan memublikasikan atau mendistribusikan ulang quote tanpa hak yang sesuai.

Lihat [SECURITY.md](SECURITY.md).

## Rencana pengembangan

- [x] Pisahkan modal bersih dari nilai pasar dan P/L.
- [x] Validasi urutan transaksi untuk mencegah pembelian atau penjualan yang tidak didukung ledger.
- [x] Harga Pegadaian dengan satuan yang dinormalisasi dan timestamp.
- [x] Quote SPY/USD/IDR dengan cache, timestamp quote terakhir, dan fallback snapshot basi.
- [x] CRUD target keuangan bebas.
- [x] Ekspor ledger ke CSV dan cadangan JSON seluruh data.
- [x] Tes otomatis untuk alur utama dan sumber data.
- [ ] Impor CSV dengan pemeriksaan dan pratinjau rekonsiliasi.
- [ ] Koreksi transaksi dengan jejak audit.
- [ ] Autentikasi jika suatu saat dibuat versi multi-pengguna atau hosting.
- [ ] Evaluasi integrasi Pegadaian resmi jika dokumentasi API publik dan izin akses yang sesuai tersedia.

## Portofolio GitHub dan LinkedIn

Panduan langkah demi langkah untuk GitHub, commit berbahasa Indonesia, ringkasan proyek, serta posting LinkedIn berada di [docs/PANDUAN_GITHUB_LINKEDIN_ID.md](docs/PANDUAN_GITHUB_LINKEDIN_ID.md). Ringkasan portofolio awal juga ada di [docs/PORTFOLIO_GUIDE_ID.md](docs/PORTFOLIO_GUIDE_ID.md).

## Lisensi

Proyek ini menggunakan [MIT License](LICENSE). Lisensi proyek tidak memberikan hak untuk mendistribusikan data pasar pihak ketiga.
