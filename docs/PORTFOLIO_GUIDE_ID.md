# Menampilkan WealthPilot di GitHub dan LinkedIn

Dokumen ini berisi teks yang bisa disesuaikan sebelum repository dipublikasikan. Jangan mengklaim integrasi otomatis Pegadaian/Pluang atau streaming tick-by-tick; versi saat ini belum menyediakan hal tersebut.

## Nama repository

`wealthpilot-personal-finance-dashboard`

## Deskripsi singkat GitHub

> Local-first personal wealth dashboard for tracking investment capital separately from market value, monitoring SPY and Pegadaian gold prices, recording transactions, and managing flexible financial goals.

## Topics GitHub

`python`, `fastapi`, `sqlite`, `personal-finance`, `investment-dashboard`, `portfolio-tracker`, `market-data`, `financial-literacy`, `vanilla-javascript`

## Ringkasan proyek untuk bagian Projects/Featured

**WealthPilot — Personal Investment & Wealth Dashboard**

Saya membangun dashboard keuangan pribadi yang membantu pengguna memisahkan modal bersih, nilai pasar, dan keuntungan/kerugian investasi. Aplikasi mencatat transaksi emas Tabungan Emas Pegadaian dan ETF SPY, menyediakan pemantauan quote beserta timestamp sumber, menampilkan arus kas portofolio, dan memungkinkan pengguna membuat target finansial sendiri.

Fokus teknis proyek ini adalah integritas pencatatan: transaksi eksternal dibedakan dari pembelian/penjualan aset, valuasi tidak diisi dengan nol ketika harga tidak tersedia, dan data yang diinput manual diberi label sumbernya. Teknologi yang digunakan meliputi Python, FastAPI, SQLite, HTML, CSS, JavaScript, serta integrasi market-data melalui API.

**Batasan yang transparan:** harga Tabungan Emas Pegadaian pada versi ini dimasukkan manual dari Tring! by Pegadaian; quote SPY dan USD/IDR bergantung pada API key serta hak akses data provider. Aplikasi belum terhubung langsung ke akun Pegadaian atau Pluang.

## Draft post LinkedIn

Saya sedang mengembangkan **WealthPilot**, personal finance dashboard yang berangkat dari masalah sederhana: modal yang disetor tidak boleh tercampur dengan nilai pasar dan keuntungan/kerugian investasi.

Fitur yang sedang saya bangun mencakup:
- Ledger transaksi untuk setoran, penarikan, pembelian, dan penjualan aset.
- Pemisahan modal bersih, nilai portofolio, P/L terealisasi, dan P/L belum terealisasi.
- Market monitor untuk SPY dan Tabungan Emas Pegadaian dengan sumber data dan timestamp yang jelas.
- Target keuangan yang bisa dibuat dan diubah pengguna sendiri.

Stack: Python, FastAPI, SQLite, HTML, CSS, JavaScript, dan API market-data.

Salah satu prinsip desainnya adalah tidak menampilkan angka yang tidak dapat diverifikasi sebagai harga live. Integrasi Pegadaian saat ini memakai input manual dari aplikasi Tring!, sementara data SPY mengikuti ketersediaan serta lisensi provider.

Proyek ini membantu saya mempraktikkan API design, data modeling, financial calculations, testing, dan dokumentasi produk. Saya akan terus menyempurnakan alur pengguna dan pengujian sebelum menambah fitur yang lebih kompleks.

#Python #FastAPI #PersonalFinance #FinTech #SoftwareDevelopment

## Saran sebelum dipublikasikan

1. Ganti deskripsi repository bila kamu ingin versi bahasa Indonesia.
2. Tambahkan link repository publik setelah kamu membuatnya di akun GitHub sendiri.
3. Unggah screenshot aplikasi yang tidak menampilkan data atau transaksi pribadi.
4. Jalankan seluruh test dan periksa file `.env`, database lokal, log, dan screenshot sebelum push.
5. Cantumkan keterbatasan sumber data agar proyek ini terlihat kredibel, bukan berlebihan dalam klaim.
