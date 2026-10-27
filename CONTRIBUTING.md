# Panduan Kontribusi

Terima kasih telah mempertimbangkan kontribusi ke WealthPilot.

## Prinsip

- Tulis komentar, dokumentasi, pesan antarmuka, dan commit proyek ini dalam bahasa Indonesia jika sesuai.
- Jangan memasukkan data akun, file `.env`, database lokal, API key, atau transaksi nyata ke commit.
- Jangan mengubah data provider menjadi harga tiruan saat provider gagal.
- Perubahan rumus keuangan wajib disertai penjelasan aturan hitung dan tes.
- Pertahankan pemisahan antara modal, nilai pasar, hasil terealisasi, dan hasil belum terealisasi.

## Alur kerja

1. Buat branch untuk satu tujuan perubahan.
2. Lakukan perubahan sekecil mungkin agar mudah ditinjau.
3. Jalankan `python -m unittest discover -s tests -v`.
4. Periksa diff dengan `git diff --check` dan `git status`.
5. Buat commit dengan format `jenis: pesan singkat dalam bahasa Indonesia`.
6. Jelaskan perilaku yang berubah, skenario tes, serta keterbatasan data pada pull request.

Jenis commit yang disarankan: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`, dan `ci`.
