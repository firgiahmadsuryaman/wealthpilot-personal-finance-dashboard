# Ringkasan Portofolio — WealthPilot

Dokumen ini berisi teks ringkas untuk profil GitHub, LinkedIn, dan CV. Sesuaikan dengan pekerjaan yang benar-benar telah kamu lakukan dan jangan mengklaim fitur yang belum tersedia.

## Nama repository

`wealthpilot-personal-finance-dashboard`

## Deskripsi singkat repository

> Dashboard keuangan dan investasi pribadi berbasis FastAPI untuk memisahkan modal bersih dari nilai pasar dan P/L, mencatat transaksi, memantau SPY serta harga Tabungan Emas Pegadaian, dan mengelola target keuangan fleksibel.

## Topik GitHub

`python`, `fastapi`, `sqlite`, `personal-finance`, `investment-dashboard`, `portfolio-tracker`, `market-data`, `financial-literacy`, `vanilla-javascript`, `indonesian`

## Ringkasan proyek

**WealthPilot — Dasbor Keuangan dan Investasi Pribadi**

WealthPilot saya kembangkan untuk mengatasi masalah pencatatan investasi: modal yang disetor harus tetap terpisah dari nilai pasar dan keuntungan atau kerugian. Aplikasi menyediakan ledger transaksi, perhitungan portofolio dengan dasar modal rata-rata tertimbang, pemantauan quote SPY dan USD/IDR, pencatatan manual harga Tabungan Emas Pegadaian dari Tring!, serta pengelolaan target keuangan yang dapat disesuaikan sendiri.

Fokus teknisnya adalah integritas data dan transparansi sumber harga. Sistem memvalidasi urutan transaksi, tidak mengubah harga yang tidak tersedia menjadi nol, menampilkan timestamp sumber, menandai quote basi, serta menyediakan ekspor ledger CSV. Proyek ini menggunakan Python, FastAPI, SQLite, HTML, CSS, JavaScript, `unittest`, dan GitHub Actions.

**Batasan yang dinyatakan dengan jelas:** harga Pegadaian saat ini dimasukkan manual dari aplikasi Tring! karena belum ada integrasi otomatis akun pribadi. Quote SPY/USD/IDR membutuhkan API key, akses instrumen, dan izin data dari provider. Aplikasi ini berjalan lokal, bukan platform trading atau layanan keuangan multi-pengguna.

## Draft post LinkedIn

Saya sedang mengembangkan **WealthPilot**, dashboard keuangan pribadi untuk membantu mencatat investasi secara lebih transparan.

Masalah yang ingin saya selesaikan sederhana: modal yang disetor tidak boleh tercampur dengan nilai pasar dan keuntungan/kerugian. Karena itu, saya membangun ledger transaksi serta perhitungan yang memisahkan modal bersih, saldo kas, nilai aset, P/L terealisasi, dan P/L belum terealisasi.

Fitur yang tersedia saat ini:
- Pencatatan setoran, penarikan, saldo awal aset, pembelian, penjualan, dan dividen.
- Pemantauan quote SPY dan kurs USD/IDR melalui API market-data.
- Histori harga Tabungan Emas Pegadaian berdasarkan snapshot yang dicatat dari aplikasi Tring!.
- Target keuangan yang dapat dibuat dan diubah sesuai kebutuhan pengguna.
- Ekspor transaksi CSV serta pengujian otomatis.

**Stack:** Python, FastAPI, SQLite, HTML, CSS, JavaScript, unittest, GitHub Actions.

Salah satu prinsip desainnya adalah tidak menyebut data basi sebagai real-time dan tidak mengisi harga yang hilang dengan angka palsu. Proyek ini juga menjadi latihan saya dalam API design, pemodelan data, pengujian logika keuangan, dokumentasi, serta pengelolaan versi dengan Git.

Repository: [tambahkan tautan repository GitHub setelah dipublikasikan]

#Python #FastAPI #FinTech #PersonalFinance #SoftwareDevelopment #GitHub

## Sebelum dipublikasikan

1. Jalankan tes dan pastikan semuanya lulus.
2. Gunakan screenshot demo tanpa saldo atau transaksi pribadi.
3. Periksa `.env`, database lokal, log, serta file ekspor sebelum `git push`.
4. Pastikan README menyebut batasan integrasi harga dan status data dengan jujur.
5. Setelah repository publik tersedia, tambahkan tautan langsung ke bagian Featured atau Projects di LinkedIn.
