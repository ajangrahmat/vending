# 05. Menghubungkan Arduino dengan serial

Komunikasi serial berada di `serial_controller.py`. Modul ini memakai
`pyserial` untuk membuka port, menunggu pesan `READY`, mengirim nomor slot,
dan menunggu konfirmasi `DONE`.

## Mengatur port

1. Hubungkan Arduino atau ESP32 ke komputer.
2. Buka Device Manager, lalu cari nomor port di bagian Ports (COM & LPT).
3. Isi `.env`, misalnya `VENDING_SERIAL_PORT=COM3`.
4. Biarkan baud rate `9600`, kecuali sketch dan aplikasi sama-sama diubah.
5. Jalankan aplikasi. Status Arduino harus menunjukkan `Siap`.
6. Sebelum membuat QR pembayaran, aplikasi mengirim `PING` dan menunggu
   jawaban `PONG` untuk memastikan kontroler masih merespons.

## Mencocokkan motor dan slot

Setiap produk punya angka `slot` di daftar `DEFAULT_PRODUCTS` pada
`inventory.py`. Slot 1 memakai pin pertama di sketch, slot 2 memakai pin
kedua, dan seterusnya. Nomor slot harus unik dan dari 1 sampai 6. Ubah angka
slot atau susunan pin jika kabel mesin berbeda.

Sketch ada di `firmware/vending_controller/vending_controller.ino`.
`RELAY_ACTIVE_LOW` mengatur polaritas modul relay. `DISPENSE_DURATION_MS`
mengatur lama motor menyala; sesuaikan dan uji untuk mesin yang digunakan.

## Pesan yang dipakai

- Arduino mengirim `READY` setelah mulai.
- Aplikasi mengirim `PING`; Arduino menjawab `PONG` sebelum pembayaran live.
- Aplikasi mengirim `DISPENSE,<slot>`.
- Arduino mengirim `DONE,<slot>` setelah motor selesai atau
  `ERROR,<alasan>` jika perintah tidak dapat dijalankan.

`DONE` mengonfirmasi durasi output motor sudah selesai; sketch ini belum
memakai sensor untuk memastikan produk benar-benar jatuh ke tempat
pengambilan.

Pembayaran live tidak dimulai sebelum Arduino siap. Jika pembayaran sudah
diterima tetapi konfirmasi motor gagal, aplikasi mengunci pesanan dan
menampilkan peringatan operator. Jangan mencoba menagih pelanggan lagi;
periksa log dan kondisi mesin secara manual.

Tes serial memakai perangkat tiruan:

```powershell
py test_serial_controller.py
```

Tes tiruan tidak memeriksa kabel, tegangan, pin, polaritas relay, atau durasi
mekanis. Periksa konfigurasi tersebut dan lakukan uji aman dengan mesin
sebenarnya sebelum digunakan.
