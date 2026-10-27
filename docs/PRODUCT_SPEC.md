# Spesifikasi Produk — WealthPilot

## 1. Pernyataan produk

WealthPilot adalah dashboard keuangan dan investasi pribadi yang membantu pengguna memahami uang yang telah dimasukkan, nilai aset saat ini, keuntungan/kerugian, kualitas data harga, dan perkembangan target keuangan.

## 2. Pengguna utama

Versi awal ditujukan untuk satu pengguna yang mengelola penghasilan freelance tidak menentu, uang tunai, Tabungan Emas Pegadaian, ETF SPY, dan target keuangan pribadi. Produk ini local-first, bukan layanan multi-pengguna.

## 3. Masalah yang ingin diselesaikan

1. Modal sering dianggap sama dengan nilai investasi saat ini.
2. Perubahan harga tidak bermakna bila sumber serta waktu pembaruan tidak terlihat.
3. Penghasilan tidak menentu membuat komitmen investasi bulanan yang kaku kurang sesuai.
4. Target keuangan perlu dapat dibuat pengguna sendiri, bukan dibatasi template tertentu.
5. Harga yang hilang tidak boleh diganti angka nol.
6. Transaksi harus ditolak jika membuat jumlah aset atau kas tidak masuk akal.

## 4. Prinsip produk

- Ledger transaksi adalah sumber utama perhitungan portofolio.
- Setoran, penarikan, pembelian, penjualan, dan nilai pasar dibedakan.
- Semua angka harga membawa konteks sumber dan timestamp bila tersedia.
- Harga manual diberi label sebagai snapshot manual.
- Harga yang basi bisa ditampilkan untuk konteks, tetapi harus ditandai.
- Target keuangan tidak dianggap sebagai saldo rekening atau investasi aktual tanpa rekonsiliasi eksplisit.
- Aplikasi tidak meminta kredensial, PIN, OTP, atau token sesi aplikasi finansial lain.
- Tidak ada pembelian/penjualan otomatis atau saran investasi yang dijamin.

## 5. Lingkup MVP

- Pencatatan setoran, penarikan, saldo awal aset, pembelian, penjualan, biaya, dan dividen.
- Ringkasan kas, modal bersih, nilai pasar bila lengkap, realized P/L, dan unrealized P/L.
- Harga beli/jual kembali Tabungan Emas Pegadaian yang dimasukkan dari Tring! beserta histori.
- Quote SPY dan USD/IDR dari provider yang dikonfigurasi.
- Histori quote dan label kualitas data.
- CRUD target keuangan bebas.
- Ringkasan arus kas serta komposisi aset.
- Ekspor ledger CSV.
- Pengujian dan workflow CI.

## 6. Di luar lingkup saat ini

- Login atau sinkronisasi saldo otomatis ke Tring! atau Pluang.
- Streaming harga tick-by-tick yang dijamin.
- Eksekusi order trading atau auto-buy/auto-sell.
- Multi-pengguna, penyimpanan cloud, atau pengelolaan akun pelanggan.
- Rekonsiliasi otomatis target dengan saldo bank atau investasi.
- Jaminan imbal hasil atau nasihat keuangan yang dipersonalisasi.

## 7. Kontrak sumber data

### Pegadaian

Pengguna mencatat harga beli nasabah dan harga jual kembali yang terlihat di Tring!, satuan harga yang tepat, serta waktu pengamatan. Valuasi menggunakan harga jual kembali. Data ini tidak dianggap feed kontinyu atau harga yang selalu berubah setiap detik.

### SPY dan USD/IDR

Quote diambil dari Twelve Data saat API key dikonfigurasi. Akses, tingkat keterlambatan, interval pembaruan, dan izin display tergantung paket serta lisensi provider. Nilai SPY dalam IDR adalah estimasi berdasarkan harga quote dan quote USD/IDR, bukan harga eksekusi Pluang.

## 8. Aturan hitung

- Modal bersih = setoran eksternal + dasar modal aset saldo awal − penarikan eksternal.
- Kas = setoran − penarikan − pembelian + hasil penjualan bersih + dividen bersih.
- Dasar modal aset yang terjual dihitung dengan metode rata-rata tertimbang.
- P/L belum terealisasi = nilai pasar terkini − dasar modal aset yang masih dimiliki.
- P/L total hanya disajikan sebagai angka lengkap ketika semua aset yang dimiliki memiliki valuasi; harga yang hilang tidak otomatis diartikan nol.
- Persentase emas membandingkan dua snapshot harga jual kembali yang tercatat berurutan. Persentase SPY mengikuti provider terhadap penutupan sebelumnya.

## 9. Kriteria keberhasilan MVP

- Instalasi baru tidak berisi saldo dan harga palsu.
- Modal, nilai pasar, dan P/L tampil terpisah.
- Pembelian tanpa saldo kas tercatat dan penjualan melebihi kepemilikan ditolak.
- Harga emas yang diinput per 0,01 gram dinormalisasi dengan benar.
- Quote provider menggunakan timestamp quote terakhir jika tersedia; kegagalan provider tidak mengubah harga menjadi nol.
- Pengguna dapat membuat, mengubah, dan menghapus target sendiri.
- Ledger dapat diekspor ke CSV.
- Tes inti berjalan sebelum commit dan otomatis pada GitHub Actions.
