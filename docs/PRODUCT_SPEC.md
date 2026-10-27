# Spesifikasi Produk — WealthPilot

## 1. Pernyataan produk

WealthPilot adalah dashboard keuangan dan investasi pribadi untuk memahami uang yang sudah disetorkan, nilai aset saat ini, keuntungan/kerugian, kualitas sumber harga, serta kemajuan menuju target keuangan.

## 2. Pengguna utama

Versi awal ditujukan untuk satu pengguna yang mengelola pendapatan freelance tidak menentu, uang kas, benchmark harga emas spot, ETF SPY, dan target keuangan yang dibuat sendiri. Produk ini local-first dan bukan layanan multi-pengguna.

## 3. Masalah yang ingin diselesaikan

1. Modal sering dianggap sama dengan nilai investasi saat ini.
2. Perubahan harga tidak berguna bila sumber dan timestamp tidak terlihat.
3. Pendapatan tidak menentu membuat kewajiban investasi bulanan yang kaku kurang sesuai.
4. Target keuangan seharusnya dapat dibuat pengguna sendiri.
5. Harga yang hilang tidak boleh diganti nol atau angka rekaan.
6. Transaksi perlu ditolak jika membuat kas atau kuantitas aset tidak masuk akal.
7. Harga spot global tidak boleh digambarkan sebagai harga eksekusi lokal.

## 4. Prinsip produk

- Ledger transaksi adalah sumber utama modal, biaya, jumlah aset, dan P/L.
- Setoran, penarikan, pembelian, penjualan, serta nilai pasar adalah konsep berbeda.
- Setiap quote disertai sumber, timestamp, unit, dan status data bila tersedia.
- Harga stale dapat ditampilkan untuk konteks, tetapi harus diberi label.
- Ask dan bid harus diterangkan dari perspektif pengguna: ask = estimasi biaya membeli dari dealer sumber; bid = estimasi penerimaan ketika menjual ke dealer sumber.
- Semua harga emas IDR bergantung pada quote USD/IDR yang valid; tanpa FX, sistem tidak membuat angka IDR.
- Quote spot emas adalah benchmark global, bukan harga resmi Pegadaian/Pluang atau janji harga eksekusi di Indonesia.
- Transaksi dicatat menggunakan harga aktual dari bukti transaksi; harga benchmark tidak otomatis dianggap sebagai harga transaksi.
- Aplikasi tidak meminta kredensial akun keuangan dan tidak melakukan auto-buy/auto-sell.

## 5. Lingkup MVP

- Pencatatan setoran, penarikan, saldo awal aset, pembelian, penjualan, biaya, dan dividen.
- Ringkasan kas, modal bersih, nilai pasar, realized P/L, dan unrealized P/L.
- Quote emas spot XAU bid/ask dan histori dari Standard Bullion.
- Quote SPY dan kurs USD/IDR dari Twelve Data.
- Timestamp, cache, status kesegaran, dan pesan kesalahan provider.
- CRUD target keuangan generik.
- Ringkasan arus kas serta komposisi aset.
- Ekspor ledger CSV dan cadangan JSON.
- Tes otomatis dan workflow CI.

## 6. Di luar lingkup saat ini

- Integrasi login atau sinkronisasi saldo pribadi dari Tring! Pegadaian atau Pluang.
- Harga beli dan buyback resmi Tabungan Emas Pegadaian secara otomatis.
- Streaming tick-by-tick yang dijamin atau prediksi harga pasti.
- Eksekusi order, auto-buy/auto-sell, atau saran imbal hasil terjamin.
- Multi-pengguna, cloud sync, atau pengelolaan rekening pelanggan.
- Rekonstruksi historis harga emas rupiah memakai histori USD/IDR pada setiap waktu historis.

## 7. Kontrak sumber data

### Emas spot XAU

`Standard Bullion /spot-prices.json` menyediakan ask dan bid dalam USD/troy ounce serta timestamp dan perubahan hari ini. `ask` dipakai sebagai harga indikatif membeli dari dealer sumber, sementara `bid` sebagai harga indikatif menjual kembali ke dealer sumber. Kurs USD/IDR dari Twelve Data digunakan untuk estimasi IDR/gram. Atribusi `Data by Standard Bullion` harus ditampilkan.

Sumber ini bukan harga resmi Tabungan Emas Pegadaian dan bukan jaminan harga eksekusi di Indonesia. Harga yang terlihat di Tring! dapat berbeda karena karakteristik produk, spread, premi, biaya, dan aturan penyedia.

### SPY dan USD/IDR

Quote diambil dari Twelve Data setelah API key dikonfigurasi. Akses data, keterlambatan, jumlah request, dan izin tampilan mengikuti paket/lisensi pengguna. Nilai SPY dalam IDR hanyalah estimasi berdasarkan quote SPY dan USD/IDR.

## 8. Aturan perhitungan

- Modal bersih = setoran eksternal + dasar modal aset saldo awal − penarikan eksternal.
- Kas = setoran − penarikan − pembelian + hasil penjualan bersih + dividen bersih.
- Dasar modal aset terjual menggunakan metode rata-rata tertimbang.
- P/L belum terealisasi = nilai pasar aset yang dimiliki − dasar modal aset tersisa.
- P/L total hanya disajikan jika valuasi semua kepemilikan cukup lengkap.
- Emas dinilai dengan estimasi harga bid spot IDR/gram. Ini bukan harga buyback Pegadaian.
- Harga transaksi tetap berasal dari transaksi aktual, bukan quote pasar yang ditampilkan.
- Persentase perubahan spot XAU mengikuti `changeToday` provider dalam konteks XAU/USD; perubahan nilai aset dalam IDR juga dapat dipengaruhi perubahan USD/IDR.

## 9. Kriteria keberhasilan MVP

- Instalasi baru tidak memiliki saldo atau harga investasi contoh.
- Modal, nilai pasar, dan P/L tampil terpisah.
- Feed emas menampilkan ask/bid, timestamp, atribusi, status, dan caveat sumber.
- Perubahan harga emas tidak ditampilkan sebagai harga resmi Pegadaian.
- Tanpa FX valid, aplikasi tidak membuat harga emas IDR.
- Data stale tidak dilabeli real-time.
- Pengguna dapat mengelola target sendiri.
- Ledger dapat diekspor ke CSV dan tes inti dapat berjalan secara lokal maupun melalui CI.
