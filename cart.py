"""Aturan keranjang dan pengembalian stok."""


def add_to_cart(products, order_items, index):
    """Masukkan satu produk ke pesanan, atau kembalikan None jika stok habis."""
    item = products[index]
    if item['stock'] <= 0:
        return None
    item['stock'] -= 1
    order_items.append(item['name'])
    return item

def remove_from_cart(products, order_items, name):
    """Hapus satu produk dari pesanan dan kembalikan stoknya."""
    if name not in order_items:
        return None
    order_items.remove(name)
    item = next(item for item in products if item['name'] == name)
    item['stock'] += 1
    return item


def clear_cart(products, order_items):
    """Kosongkan pesanan dan kembalikan stok untuk semua isinya."""
    if not order_items:
        return False
    for name in order_items:
        item = next(item for item in products if item['name'] == name)
        item['stock'] += 1
    order_items.clear()
    return True


def summarize_cart(order_items, products):
    """Susun daftar (nama, jumlah, harga satuan) sesuai urutan dipilih."""
    quantity_by_name = {}
    order = []
    for name in order_items:
        if name not in quantity_by_name:
            order.append(name)
            quantity_by_name[name] = 0
        quantity_by_name[name] += 1

    price_by_name = {item['name']: item['price'] for item in products}
    return [
        (name, quantity_by_name[name], price_by_name[name])
        for name in order
    ]
