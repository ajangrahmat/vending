# Pelajaran 4: Menjalankan dan memeriksa aplikasi

## Menjalankan aplikasi

Dari folder proyek:

```powershell
py main.py
```

Tanpa API key, aplikasi menggunakan simulasi. Dengan API key di `.env`, mode
live SumoPod aktif; sandbox tetap menjadi pilihan default.

## Menjalankan tes tanpa transaksi

Jalankan setiap tes dari folder proyek:

```powershell
py test_main_gui.py
py test_cart.py
py test_qris_payment.py
py test_qr_checkout.py
py test_sumopod_client.py
py test_serial_controller.py
```

Tes GUI menggunakan mode simulasi dan klien pembayaran tiruan. Untuk tes
koneksi live yang benar-benar membuat transaksi sandbox, jalankan opsi `--live`
hanya ketika siap mengirim permintaan ke SumoPod.

## Jika ada masalah

- Gambar produk tidak muncul: pastikan berkas bernama sama dengan nilai
  `image` di `inventory.py` dan berada di `assets/`.
- Aplikasi masuk simulasi: periksa apakah `SUMOPOD_API_KEY` sudah terisi di
  `.env`; jangan menyalin key ke pesan atau laporan.
- QR tidak tampil: baca `machine_log.log` untuk melihat apakah link checkout
  berhasil dibuat dan apakah pengambilan QR gagal.
