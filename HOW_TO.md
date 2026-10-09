# Panduan aplikasi vending

Aplikasi dijalankan dari `main.py`. Kode dibagi berdasarkan tugas agar mudah
dicari dan diedit. Alur aplikasi menggunakan fungsi biasa dan data sederhana,
bukan class/OOP.

## Menjalankan aplikasi

```powershell
py main.py
```

Tanpa API key, aplikasi berjalan dalam mode simulasi. Untuk latihan QRIS
melalui sandbox SumoPod tanpa Arduino/ESP32, atur `.env`:

```text
MODE_DEMO=1
SUMOPOD_SANDBOX=1
```

Jika `SUMOPOD_API_KEY` tersedia, tombol akan membuat pembayaran pada SumoPod
sandbox dan menampilkan QRIS sandbox. Arduino/ESP32 tidak diperlukan; sesudah
pembayaran sandbox terkonfirmasi, aplikasi mencatat keberhasilan tetapi tidak
mengeluarkan produk fisik. Tanpa API key, pembayaran berjalan sebagai simulasi
lokal. `MODE_DEMO=1` selalu mencegah penggunaan endpoint production, termasuk
jika `SUMOPOD_SANDBOX=0`.

Untuk menggunakan alur pembayaran SumoPod bersama dispenser, atur
`MODE_DEMO=0` dan isi `SUMOPOD_API_KEY` di `.env`. Sandbox aktif secara
default. Pembayaran production hanya diaktifkan dengan `MODE_DEMO=0` dan
`SUMOPOD_SANDBOX=0`; transaksi tersebut memerlukan Arduino/ESP32 siap dan
pemeriksaan `PING`/`PONG` berhasil. Pastikan API key cocok dengan endpoint yang
dipilih. Jangan membagikan atau memasukkan API key ke dalam source code.

## Menghubungkan Arduino / ESP32

Pasang dependensi dengan `py -m pip install -r requirements.txt`, lalu
tambahkan pengaturan serial ke `.env`:

```text
VENDING_SERIAL_PORT=COM3
VENDING_SERIAL_BAUD=9600
```

Ganti `COM3` sesuai port board di Device Manager Windows. Saat
`MODE_DEMO=0` dan API key tersedia, aplikasi hanya mengizinkan pembayaran
setelah Arduino terhubung dan menjawab pemeriksaan `PING` dengan `PONG`.
Jika transaksi sudah dibayar tetapi motor gagal memberi konfirmasi, pesanan
akan dikunci dan aplikasi meminta bantuan operator; jangan meminta pelanggan
membayar ulang.

Sketch ada di `firmware/vending_controller/vending_controller.ino`. Cocokkan
nomor slot di `inventory.py` dengan kabel motor dan pin pada sketch. Nomor
slot harus unik dan berada pada rentang 1–6. Atur
`RELAY_ACTIVE_LOW` sesuai modul relay, lalu sesuaikan
`DISPENSE_DURATION_MS` berdasarkan mekanisme vending yang sebenarnya. Uji
dengan mesin aman sebelum dipakai pelanggan.

## File yang perlu diketahui

| File | Tugas | Biasanya diedit saat ingin... |
|---|---|---|
| `main.py` | Menyiapkan produk, jendela, tombol, dan seluruh alur pembayaran QRIS | Mengubah alur utama atau transaksi |
| `inventory.py` | Daftar produk dan penyimpanan stok | Mengganti nama, harga, stok awal, atau gambar |
| `vending_ui.py` | Membuat tampilan, kartu produk, panel QR, dan layar sukses | Mengubah tulisan atau tata letak |
| `theme.py` | Warna tampilan | Mengganti warna |
| `cart.py` | Aturan tambah/kurangi pesanan dan pengembalian stok | Mengubah aturan keranjang |
| `serial_controller.py` | Menghubungkan aplikasi dan mengirim perintah ke Arduino | Mengubah protokol serial |
| `firmware/vending_controller/vending_controller.ino` | Perintah Arduino dan pengaturan pin, relay, serta durasi motor | Mengubah sketch atau kabel motor |
| `qris_payment.py` | Mengambil gambar QR checkout dan memformat waktu kedaluwarsa | Mengubah pemrosesan QR checkout |
| `configuration.py` | Membaca pengaturan SumoPod dan memilih mode | Mengubah cara memilih mode pembayaran |
| `sumopod_client.py` | Komunikasi dengan API SumoPod | Mengubah detail koneksi API |
| `qr_checkout.py` | Membaca dan menggambar QR dari halaman checkout | Mengubah pemrosesan QR checkout |
| `machine_log.py` | Menulis catatan kejadian aplikasi | Mengubah lokasi atau format log |
| `stock.json` | Stok terakhir yang tersimpan otomatis | Memeriksa stok yang tersimpan |
| `assets/` | Gambar produk | Mengganti gambar produk |

### Contoh perubahan yang umum

- **Mengganti harga atau nama produk:** edit `DEFAULT_PRODUCTS` di `inventory.py`.
- **Mengubah tata letak atau tulisan:** edit fungsi pembuat tampilan di
  `vending_ui.py`.
- **Mengganti warna:** edit nilai warna di `theme.py`.
- **Mengubah aturan pesanan:** lihat fungsi-fungsi di `cart.py`.
- **Melihat catatan transaksi:** buka `machine_log.log`.

`main.py` sebaiknya tetap menjadi penghubung antarbagian. Kalau menemukan
aturan keranjang atau kode tampilan yang perlu ditambahkan, letakkan di modul
yang tugasnya sesuai agar file utama tetap mudah dibaca.

Klien SumoPod dan pembaca QR checkout adalah modul mandiri (`sumopod_client.py`
dan `qr_checkout.py`). Tidak ada paket `qrispy2` atau library OOP terpisah di
aplikasi utama.

## Pelajaran langkah demi langkah

Panduan singkat untuk mengubah aplikasi ini ada di folder `lessons/`:

1. `01_products_and_stock.md` — produk, gambar, dan penyimpanan stok.
2. `02_cart_and_interface.md` — alur keranjang dan tampilan.
3. `03_qris_and_sumopod.md` — konfigurasi dan alur pembayaran.
4. `04_run_and_test.md` — menjalankan aplikasi, tes, dan pemeriksaan masalah.

## Menjalankan pemeriksaan

```powershell
py test_main_gui.py
py test_cart.py
py test_qris_payment.py
py test_qr_checkout.py
py test_sumopod_client.py
py test_serial_controller.py
```

Tes GUI memakai mode simulasi dan menguji integrasi live dengan klien tiruan,
tanpa membuat transaksi sungguhan. Untuk membuat transaksi uji ke SumoPod,
jalankan `py test_main_gui.py --live` hanya saat memang ingin menguji koneksi.
Perintah live memerlukan API key di environment atau `.env`.
