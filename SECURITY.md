# Kebijakan Keamanan

Terima kasih telah membantu menjaga keamanan WealthPilot.

## Data yang wajib dijaga

- Jangan commit `.env`, API key, database `data/wealthpilot.db`, log, bukti transaksi, atau screenshot yang menunjukkan data pribadi.
- Jangan masukkan password, PIN, OTP, cookie, atau token sesi Pegadaian/Tring!/Pluang ke aplikasi. WealthPilot tidak mempunyai integrasi login tersebut.
- API key Twelve Data hanya disimpan di `.env`; jangan letakkan di kode browser.
- Gunakan data sintetis untuk issue, pull request, screenshot, dan demo publik.

## Cara menjalankan dengan aman

- Secara default aplikasi di-bind ke `127.0.0.1`, bukan `0.0.0.0`.
- Jangan membuka port aplikasi ke internet/LAN sebelum autentikasi, otorisasi, HTTPS, backup, pembatasan akses, perlindungan CSRF yang sesuai, dan audit keamanan dirancang.
- Data pasar mungkin memiliki batas lisensi dan larangan redistribusi; cek perjanjian provider yang digunakan.
- File CSV dan JSON cadangan berisi ledger serta data keuangan pribadi. Simpan secara aman dan jangan unggah ke repository publik.

## Melaporkan masalah

Untuk repository publik, buat laporan privat melalui mekanisme security advisory GitHub apabila tersedia. Jangan memublikasikan rahasia, token, atau detail data akun. Untuk masalah lokal, reproduksi dengan database sementara dan data sintetis.

## Pernyataan batasan

WealthPilot merupakan proyek edukasi/portofolio yang berjalan secara lokal, bukan layanan kustodian, platform order, atau penyedia nasihat keuangan. Pengguna bertanggung jawab memverifikasi harga, biaya, pajak, dan catatan transaksi terhadap sumber aslinya.
