"""Uji aturan keranjang dan stok tanpa membuka jendela."""

from cart import remove_from_cart, clear_cart, summarize_cart, add_to_cart


def main():
    products = [
        {'name': "Air", 'price': 3000, 'stock': 2},
        {'name': "Kopi", 'price': 5000, 'stock': 1},
    ]
    order_items = []

    assert add_to_cart(products, order_items, 0) == products[0]
    assert add_to_cart(products, order_items, 1) == products[1]
    assert add_to_cart(products, order_items, 0) == products[0]
    assert add_to_cart(products, order_items, 1) is None
    assert summarize_cart(order_items, products) == [
        ("Air", 2, 3000),
        ("Kopi", 1, 5000),
    ]

    assert remove_from_cart(products, order_items, "Kopi") == products[1]
    assert remove_from_cart(products, order_items, "tidak ada") is None
    assert products[1]['stock'] == 1
    assert clear_cart(products, order_items) is True
    assert order_items == []
    assert [item['stock'] for item in products] == [2, 1]
    assert clear_cart(products, order_items) is False
    print("Semua uji keranjang lulus.")


if __name__ == "__main__":
    main()
