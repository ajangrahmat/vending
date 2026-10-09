"""Daftar produk dan penyimpanan stok mesin."""

import json
import os


DISPENSER_SLOT_COUNT = 6

# Ubah nama, harga, stok awal, atau nama file gambar produk di daftar ini.
DEFAULT_PRODUCTS = [
    {'name': "Air Mineral", 'price': 3000, 'stock': 15, 'image': "air_mineral.png", 'slot': 1},
    {'name': "Kopi", 'price': 5000, 'stock': 12, 'image': "kopi.png", 'slot': 2},
    {'name': "Teh Botol", 'price': 4000, 'stock': 10, 'image': "teh_botol.png", 'slot': 3},
    {'name': "Cokelat", 'price': 3000, 'stock': 8, 'image': "coklat.png", 'slot': 4},
    {'name': "Keripik", 'price': 4000, 'stock': 7, 'image': "keripik.png", 'slot': 5},
    {'name': "Mie Instan", 'price': 5000, 'stock': 9, 'image': "mie_instan.png", 'slot': 6},
]


def create_product_list():
    """Buat salinan produk agar perubahan stok tidak mengubah nilai awal."""
    used_slots = set()
    for item in DEFAULT_PRODUCTS:
        slot = item.get('slot')
        if (
            not isinstance(slot, int)
            or isinstance(slot, bool)
            or not 1 <= slot <= DISPENSER_SLOT_COUNT
        ):
            raise ValueError(
                f"Slot dispenser {slot!r} untuk {item['name']} harus "
                f"bernomor 1 sampai {DISPENSER_SLOT_COUNT}."
            )
        if slot in used_slots:
            raise ValueError(f"Nomor slot dispenser {slot} dipakai lebih dari sekali.")
        used_slots.add(slot)

    return [
        {**item, 'initial_stock': item['stock']}
        for item in DEFAULT_PRODUCTS
    ]


def resolve_asset_path(filename):
    """Find a product image in the project assets folder."""
    if not filename or os.path.isabs(filename) or os.path.exists(filename):
        return filename
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "assets",
        filename,
    )


def load_stock(stock_file, log_event):
    """Baca stok tersimpan; entri yang rusak dilewati dan dicatat."""
    try:
        with open(stock_file, encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        log_event(f"PERINGATAN: stok tersimpan tidak terbaca ({exc}) — "
              "stok dikembalikan ke nilai bawaan")
        return {}

    if not isinstance(data, dict):
        log_event("PERINGATAN: isi stok tersimpan bukan objek JSON — "
              "stok dikembalikan ke nilai bawaan")
        return {}

    result = {}
    for name, value in data.items():
        try:
            result[str(name)] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    return result


def save_stock(stock_file, products, log_event):
    """Simpan stok secara atomik agar berkas tidak rusak jika mesin mati."""
    temporary_path = stock_file + ".tmp"
    try:
        with open(temporary_path, "w", encoding="utf-8") as file:
            json.dump({item['name']: item['stock'] for item in products},
                      file, indent=2, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, stock_file)
    except OSError as exc:
        log_event(f"GAGAL menyimpan stok: {exc}")
        try:
            os.remove(temporary_path)
        except OSError:
            pass
