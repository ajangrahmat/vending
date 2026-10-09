# Pelajaran 1: Produk dan stok

Pelajaran ini memakai kode aplikasi yang benar-benar berjalan. Semua fungsi
ditulis sebagai fungsi biasa; tidak perlu membuat class.

## Mengganti produk

Buka `inventory.py`. Daftar `DEFAULT_PRODUCTS` berisi nama, harga, stok awal,
dan nama gambar setiap produk:

```python
{'name': "Air Mineral", 'price': 3000, 'stock': 15,
 'image': "air_mineral.png"}
```

Nama berkas gambar harus cocok dengan berkas di folder `assets/`. Untuk
mengganti gambar Air Mineral, taruh gambar baru di folder itu lalu ubah nilai
`image`. Jangan hapus kunci `name`, `price`, `stock`, atau `image`: bagian UI
menggunakan semuanya.

## Cara gambar dimuat

`inventory.py` menyediakan `resolve_asset_path()`, yang mencari gambar di
folder `assets/`. `vending_ui.py` memanggil fungsi itu saat membuat kartu
produk. Referensi gambar disimpan oleh UI supaya gambar tetap terlihat selama
jendela terbuka.

## Cara stok disimpan

`main.py` memanggil `load_stock()` saat aplikasi dibuka dan `save_stock()`
setelah pesanan mengubah stok. Nilai stok terakhir disimpan di `stock.json`.
Untuk memulai lagi dengan stok awal, gunakan tombol **Kembalikan stok ke nilai
awal** di aplikasi.

## Coba sendiri

1. Ubah harga satu produk di `inventory.py`.
2. Pastikan nama berkas gambarnya tersedia di `assets/`.
3. Jalankan `py main.py` dan lihat kartu produk.
