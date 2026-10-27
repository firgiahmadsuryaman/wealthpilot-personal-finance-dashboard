# Panduan Publikasi WealthPilot ke GitHub dan LinkedIn

Panduan ini ditulis untuk pengguna Windows dan PowerShell. Pesan commit proyek menggunakan bahasa Indonesia dan dikelompokkan berdasarkan tujuan perubahan.

## Bagian A — Pemeriksaan sebelum upload

Buka PowerShell pada folder proyek dan jalankan:

```powershell
git status
git log --oneline --decorate
git diff --check
python -m unittest discover -s tests -v
```

Pastikan tes lulus. Pastikan file berikut **tidak pernah ditambahkan** ke Git:

- `.env` (berisi API key)
- `data/wealthpilot.db` atau database SQLite lain
- `.venv/`
- file CSV transaksi pribadi
- screenshot dengan nama, saldo, nomor rekening, atau detail pribadi

Periksa bahwa `.gitignore` aktif:

```powershell
git check-ignore .env data/wealthpilot.db .venv
```

Jika `.env` atau database pernah ter-commit pada masa lalu, menambah `.gitignore` saja tidak menghapusnya dari riwayat. Hapus dari riwayat Git dan rotasi API key yang terlanjur terekspos sebelum repository dipublikasikan.

## Bagian B — Struktur commit yang disarankan

Gunakan pesan commit yang menjelaskan satu perubahan dengan jelas, bukan pesan seperti `update`, `fix`, `coba`, atau `final`. Format yang digunakan:

`jenis: ringkasan perubahan dalam bahasa Indonesia`

Jenis yang dianjurkan:

- `feat`: fitur baru
- `fix`: perbaikan bug
- `test`: penambahan/perbaikan tes
- `docs`: dokumentasi
- `refactor`: perapian struktur tanpa mengubah tujuan fitur
- `chore`: pekerjaan pemeliharaan
- `ci`: otomasi pengujian

Riwayat proyek disiapkan secara bertahap dengan pesan berbahasa Indonesia. Commit awal pada paket ini menggunakan identitas teknis `WealthPilot Developer` agar tidak mengaku sebagai akun pribadimu; sebelum membuat commit baru, konfigurasikan nama dan e-mail Git yang benar milikmu untuk repository ini:

```powershell
git config --local user.name "NAMA GITHUB MILIKMU"
git config --local user.email "EMAIL GITHUB TERVERIFIKASI"
git config --local user.name
git config --local user.email
```

Perintah tersebut mengatur identitas untuk commit berikutnya. Jangan mengganti identitas commit lama agar terlihat seolah-olah kamu mengerjakan perubahan historis itu sendiri. Untuk pengembangan selanjutnya, gunakan contoh commit berikut hanya bila perubahan tersebut benar-benar dilakukan:

```text
feat: tambahkan ekspor transaksi ke CSV
fix: gunakan timestamp quote terakhir dari penyedia data
fix: tandai data pasar lama sebagai basi
fix: validasi urutan transaksi sebelum menyimpan ledger
feat: tambahkan penyuntingan transaksi yang tervalidasi
fix: tutup koneksi SQLite setelah operasi selesai
test: uji pembelian tanpa saldo kas yang cukup
test: uji konversi harga emas per 0,01 gram
test: uji fallback quote saat penyedia data gagal
test: uji ekspor CSV dan penanganan teks spreadsheet
docs: terjemahkan panduan instalasi ke bahasa Indonesia
docs: jelaskan metode perhitungan modal dan keuntungan
ci: jalankan tes pada beberapa versi Python
```

Jangan membuat commit kosong atau mengklaim perubahan yang tidak dilakukan hanya untuk menambah jumlah commit. Commit terstruktur harus mencerminkan perubahan yang nyata dan bisa ditinjau.

Untuk perubahan baru, alur normal:

```powershell
git add app tests docs README.md
git diff --cached
git commit -m "fix: jelaskan perubahan yang benar-benar dilakukan"
```

Lebih baik satu commit memuat satu kelompok perubahan yang koheren daripada memasukkan seluruh proyek setiap kali.

## Bagian C — Membuat repository baru di GitHub

1. Buka [GitHub](https://github.com/) dan masuk ke akunmu.
2. Klik tombol **New repository**.
3. Isi nama: `wealthpilot-personal-finance-dashboard`.
4. Tulis deskripsi: `Dashboard keuangan dan investasi pribadi dengan pencatatan modal, nilai pasar, dan P/L yang terpisah.`
5. Tentukan public atau private. Untuk portofolio, biasanya public setelah audit rahasia dan data selesai.
6. Pilih lisensi sesuai kebutuhan. Repository lokal ini sudah memiliki MIT License.
7. Jika ingin memakai riwayat commit lokal yang sudah disiapkan, buat repository GitHub dalam keadaan kosong—jangan meminta GitHub membuat README, `.gitignore`, atau commit awal lain.
8. Salin URL repository, biasanya `https://github.com/USERNAME/wealthpilot-personal-finance-dashboard.git`.

Di PowerShell pada folder proyek, jalankan perintah berikut dan ganti URL placeholder dengan URL asli:

```powershell
git remote add origin https://github.com/USERNAME/wealthpilot-personal-finance-dashboard.git
git branch -M main
git push -u origin main
```

Jangan mengetik `USERNAME` apa adanya. Gunakan nama akun GitHub milikmu. Jika `origin` sudah ada, periksa dengan `git remote -v`; jangan menambahkan remote yang sama dua kali.

Setelah push, refresh repository GitHub. Periksa README, folder `app`, `tests`, `docs`, workflow Actions, serta halaman commit. Bila GitHub Actions merah, buka tab **Actions**, pilih run yang gagal, lalu baca langkah tes yang gagal sebelum melanjutkan.

## Bagian D — Jika repository GitHub sudah ada

Sebelum push, periksa remote dan riwayat lokal:

```powershell
git remote -v
git status
git log --oneline --graph --decorate -15
```

Jangan menjalankan `git push --force` atau menghapus riwayat remote tanpa memahami konsekuensinya. Jika repository sudah memiliki commit awal yang berbeda, lebih aman menyelaraskan riwayat secara terencana atau mengunggah proyek ke repository baru.

## Bagian E — Perbarui proyek setelah commit awal

Setiap kali ada perubahan yang sudah diuji:

```powershell
python -m unittest discover -s tests -v
git diff --check
git status
git add app tests docs README.md CHANGELOG.md
git commit -m "test: tambahkan pengujian untuk perubahan terbaru"
git push
```

Ganti nama commit dengan perubahan yang benar-benar dibuat. Jika tidak ada file berubah, jangan membuat commit kosong.

## Bagian F — Memasang proyek di LinkedIn

### Menambahkan ke Projects atau Featured

1. Buka profil LinkedIn.
2. Tambahkan bagian **Projects** atau **Featured** melalui menu penambahan bagian profil.
3. Nama proyek: **WealthPilot — Dasbor Keuangan dan Investasi Pribadi**.
4. Tambahkan tautan repository GitHub publik.
5. Gunakan deskripsi di bawah dan sesuaikan dengan kontribusi yang benar-benar kamu lakukan.

**Deskripsi proyek untuk LinkedIn:**

> Mengembangkan dashboard keuangan dan investasi pribadi menggunakan Python, FastAPI, SQLite, HTML, CSS, dan JavaScript. Aplikasi memisahkan modal bersih dari nilai pasar serta keuntungan/kerugian, mencatat transaksi dengan validasi saldo dan kuantitas, memantau quote SPY/USD/IDR melalui API market-data, menyimpan snapshot harga Tabungan Emas Pegadaian dari input Tring!, mengelola target keuangan fleksibel, dan mengekspor ledger ke CSV. Proyek dilengkapi pengujian otomatis dan dokumentasi. Integrasi harga Pegadaian masih berupa input manual; aplikasi berjalan lokal dan belum mengeksekusi transaksi.

### Contoh post LinkedIn

> Saya mengembangkan **WealthPilot**, sebuah dashboard keuangan pribadi untuk mencatat investasi dengan lebih transparan.
>
> Fokus utama proyek ini adalah membedakan modal yang disetor dari nilai pasar dan keuntungan/kerugian. Saya membangun ledger transaksi, validasi urutan transaksi, perhitungan dasar modal rata-rata tertimbang, monitoring quote dengan timestamp, pengelolaan target fleksibel, ekspor CSV, dan tes otomatis.
>
> Teknologi: Python, FastAPI, SQLite, HTML, CSS, JavaScript, unittest, dan GitHub Actions.
>
> Saya juga menjaga batasan sumber data tetap jelas: harga Tabungan Emas Pegadaian dimasukkan dari snapshot aktual yang terlihat di Tring!, sedangkan quote SPY dan USD/IDR bergantung pada akses serta lisensi penyedia data. Proyek ini belum menjadi aplikasi trading dan belum terhubung langsung ke akun broker.
>
> Repository: [tempel tautan GitHub]
>
> #Python #FastAPI #FinTech #PersonalFinance #SoftwareDevelopment

### Gambar pendukung

Gunakan screenshot demo yang bersih dan tidak menampilkan saldo pribadi atau transaksi asli. Bila database lokal berisi data nyata, jangan mengunggah screenshot sebelum menggantinya dengan data demo yang sengaja dibuat untuk demonstrasi.

## Bagian G — Checklist akhir

- [ ] README berbahasa Indonesia menjelaskan instalasi, fitur, perhitungan, dan batasan.
- [ ] Tes lulus secara lokal.
- [ ] GitHub Actions lulus setelah push.
- [ ] Tidak ada `.env`, database, CSV, log, atau screenshot pribadi di repository.
- [ ] Tidak ada klaim otomatisasi Pegadaian yang belum tersedia.
- [ ] URL GitHub di profil/post LinkedIn benar dan bisa dibuka.
- [ ] Commit bermakna, terstruktur, dan ditulis dalam bahasa Indonesia.
