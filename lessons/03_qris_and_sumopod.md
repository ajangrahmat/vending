# Pelajaran 3: QRIS dan SumoPod

Kode pembayaran berjalan dalam mode simulasi jika API key belum diisi. Saat
API key tersedia, `configuration.py` membuat klien SumoPod dan mengaktifkan
mode sandbox secara default.

## Mengatur koneksi

Simpan pengaturan lokal di `.env`:

```text
SUMOPOD_API_KEY=isi_api_key_di_sini
SUMOPOD_SANDBOX=1
```

Jangan tempelkan API key ke kode program atau bagikan file `.env`. Untuk
berpindah ke transaksi sungguhan, atur `SUMOPOD_SANDBOX=0` hanya jika memang
sudah siap menerima pembayaran nyata.

## Alur tombol Bayar

Seluruh penghubung pembayaran aplikasi berada di `main.py`:

1. `start_payment()` memeriksa pesanan dan memulai worker pembayaran.
2. `process_live_payment()` meminta payment link melalui
   `SumoPodClient.create_payment()`.
3. `fetch_checkout_qr()` di `qris_payment.py` mengambil matriks QR dari halaman
   checkout dan membuat gambarnya.
4. Status pembayaran diperiksa berkala melalui klien SumoPod.
5. Pembayaran berhasil memanggil `dispense_product()`; pembatalan menghentikan
   pemeriksaan dan memperbarui tampilan.

`sumopod_client.py` menangani komunikasi API. `qr_checkout.py` membaca QR dari
HTML checkout. `vending_ui.py` menampilkan gambar QR; file UI tidak membuat
transaksi sendiri.

## Menguji dengan aman

`py test_main_gui.py` memeriksa alur live memakai klien tiruan, tanpa membuat
transaksi. Jangan menjalankan `py test_main_gui.py --live` kecuali memang
bermaksud membuat transaksi sandbox SumoPod.
