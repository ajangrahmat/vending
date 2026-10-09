# Pelajaran 2: Keranjang dan tampilan

Alur utama menghubungkan modul-modul kecil dengan fungsi biasa.

## Menambahkan produk ke pesanan

Di `main.py`, tombol kartu produk memanggil `select_product(index)`. Fungsi itu:

1. Memastikan pembayaran tidak sedang berjalan.
2. Memanggil `add_to_cart()` dari `cart.py`.
3. Memperbarui total, kartu produk, tampilan pesanan, dan stok tersimpan.

`cart.py` menangani perubahan isi pesanan. `vending_ui.py` hanya membuat dan
memperbarui widget—aturan pesanan tidak diletakkan di sana.

## Mengubah tampilan

Buka `vending_ui.py` jika ingin mengubah tata letak, label, atau tombol.
Callback seperti `select_product` dan `start_qris_payment` diterima melalui
parameter `actions`. Dengan begitu tombol memanggil fungsi di `main.py` tanpa
mencampurkan aturan transaksi dengan kode widget.

## Mengubah warna

Warna yang dipakai aplikasi disimpan di `theme.py`. Ubah nilai warna di sana,
lalu jalankan aplikasi untuk memeriksa hasilnya.

## Coba sendiri

1. Cari fungsi `select_product()` di `main.py`.
2. Ikuti pemanggilannya ke `add_to_cart()` di `cart.py`.
3. Cari fungsi `update_order()` di `vending_ui.py` untuk melihat bagaimana
   isi pesanan ditampilkan.
