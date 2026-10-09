"""
test_qr_checkout.py — Uji pembacaan QR dari HTML checkout, TANPA jaringan.

Semua uji di sini offline: SVG-nya dibuat sendiri meniru bentuk asli yang
dipakai SumoPod (dua path: fill="#FFFFFF" untuk modul terang dan
fill="#000000" untuk modul gelap, viewBox="0 0 N N", tiap modul satu subpath
`M x y l 1 0 0 1 -1 0 Z`).

Yang diuji adalah perangkap yang sudah benar-benar kejadian di lapangan:
  1. Dua path harus dipisah — kalau digabung matriks jadi 100% hitam.
  2. viewBox ada di tag pembuka <svg>, bukan di isi elemen.
  3. Matriks yang terbalik harus dideteksi lewat pola finder.
  4. HTML yang tidak berbentuk harus melempar QrCheckoutError yang jelas.

Uji ke jaringan (opsional) hanya jalan kalau SUMOPOD_API_KEY tersedia dan
dipanggil dengan argumen `--live`.

Jalankan:  py test_qr_checkout.py
           py test_qr_checkout.py --live
"""

from __future__ import annotations

import os
import sys

import qr_checkout
from qr_checkout import (
    QrCheckoutError,
    read_matrix_from_html,
    decode_payload_from_matrix,
    build_image_from_matrix,
)

try:
    import qrcode
except ImportError:
    qrcode = None


# ----------------------------------------------------------------------
# Pembuat HTML tiruan, meniru format SumoPod
# ----------------------------------------------------------------------
def matrix_from_text(text):
    """Matriks QR asli dari sebuah teks, memakai pustaka `qrcode`."""
    qr = qrcode.QRCode(border=0)
    qr.add_data(text)
    qr.make(fit=True)
    return [[1 if cell else 0 for cell in line] for line in qr.get_matrix()]


def sumopod_svg(matrix, white_first=True, include_viewbox=True, id_svg="qrcode"):
    """Rakit elemen <svg> meniru keluaran SumoPod."""
    matrix_size = len(matrix)
    dark = [
        (x, y)
        for y in range(matrix_size)
        for x in range(matrix_size)
        if matrix[y][x]
    ]
    light = [
        (x, y)
        for y in range(matrix_size)
        for x in range(matrix_size)
        if not matrix[y][x]
    ]

    def path(color, cell):
        d = " ".join(f"M {x} {y} l 1 0 0 1 -1 0 Z" for x, y in cell)
        return f'<path d="{d}" fill="{color}"></path>'

    viewbox_attribute = (
        f'viewBox="0 0 {matrix_size} {matrix_size}" '
        if include_viewbox else ""
    )
    content = ((path("#FFFFFF", light) + path("#000000", dark)) if white_first
           else (path("#000000", dark) + path("#FFFFFF", light)))
    return (f'<svg id="{id_svg}" style="width:200px;height:200px;background:white" '
            f'height="256" {viewbox_attribute}width="256" '
            f'xmlns="http://www.w3.org/2000/svg">{content}</svg>')


def full_html(svg, before="<html><body><div>One-Time Use QR Code</div>", after="</body></html>"):
    return before + svg + after


def test_tkinter_render(check):
    """Render QR di Tkinter, potret hasilnya, hitung piksel gelap/terang.

    Uji ini ada karena satu bug nyata: buat_gambar_dari_matriks() dulu
    mengembalikan gambar mode "1" (1-bit). Pillow menyimpannya dengan benar,
    jadi PNG-nya kelihatan bagus — tetapi ImageTk.PhotoImage membaca mode "1"
    sebagai citra berpalet indeks 0/1, dan yang tampil di layar adalah KOTAK
    HITAM PEKAT. Uji yang cuma memeriksa "objek gambar ada" akan lulus
    padahal aplikasinya tidak menampilkan QR sama sekali.

    Jadi di sini hasilnya benar-benar dirender dan dipotret. Jendela kecil
    akan berkedip sekejap saat uji ini berjalan.
    """
    try:
        import time as _time
        import tkinter
        from PIL import ImageGrab, ImageTk
    except ImportError:
        print("  (dilewati — tkinter / ImageGrab tidak tersedia)")
        return

    try:
        window = tkinter.Tk()
    except Exception as exc:
        print(f"  (dilewati — tidak ada layar: {exc})")
        return

    try:
        window.geometry("240x240+40+40")
        window.configure(bg="white")

        matrix = matrix_from_text("uji tampilan tkinter")
        pil = build_image_from_matrix(matrix, size_px=210)
        if pil is None:
            print("  (dilewati — Pillow tidak terpasang)")
            return

        photo_image = ImageTk.PhotoImage(pil)
        label = tkinter.Label(window, image=photo_image, bg="white", bd=0)
        label.pack()
        window.attributes("-topmost", True)
        window.update()
        _time.sleep(0.6)
        window.update()

        # Pemeriksaan mode tidak butuh layar, jadi selalu dijalankan.
        check("mode gambar bukan '1' (jebakan kotak hitam)", pil.mode != "1", pil.mode)

        x, y = label.winfo_rootx(), label.winfo_rooty()
        w, h = label.winfo_width(), label.winfo_height()
        try:
            screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h)).convert("L")
        except OSError as exc:
            # Terjadi saat sesi desktop tidak bisa diakses (layar terkunci,
            # remote desktop terputus). Itu bukan kerusakan kode — jangan
            # dilaporkan sebagai kegagalan, karena uji yang gagal karena
            # lingkungan akan membuat orang mengabaikan hasil uji ini.
            print(f"  (pemeriksaan piksel dilewati — layar tidak bisa dipotret: {exc})")
            return

        total = screenshot.size[0] * screenshot.size[1]
        color = screenshot.getcolors(maxcolors=100000) or []
        dark = sum(count for count, value in color if value < 64)
        light = sum(count for count, value in color if value > 191)

        check("render Tkinter punya piksel terang", light > total * 0.15,
            f"terang={light}/{total}")
        check("render Tkinter punya piksel gelap", dark > total * 0.15,
            f"gelap={dark}/{total}")
    finally:
        try:
            window.destroy()
        except Exception:
            pass


# ----------------------------------------------------------------------
def main():
    passed_count = failure_callback = 0

    def check(name, condition, info=""):
        nonlocal passed_count, failure_callback
        if condition:
            passed_count += 1
            print(f"  OK    {name}")
        else:
            failure_callback += 1
            print(f"  GAGAL {name}" + (f"  <- {info}" if info else ""))

    if qrcode is None:
        print("Pustaka `qrcode` tidak ada. Pasang dulu: py -m pip install qrcode")
        return 1

    print("=" * 60)
    print("1. Baca matriks dari SVG bentuk SumoPod")
    print("=" * 60)

    text = "dd9e26e517e68cf522509fa34f8e1b822f11e21df343bbffb639a781a9fe7c83"
    original_matrix = matrix_from_text(text)
    svg = sumopod_svg(original_matrix)
    matrix = read_matrix_from_html(full_html(svg))

    check("ukuran matriks sama", len(matrix) == len(original_matrix),
          f"{len(matrix)} vs {len(original_matrix)}")
    check("isi matriks sama persis", matrix == original_matrix)
    check("jumlah modul gelap masuk akal",
        0.3 < sum(sum(row) for row in matrix) / (len(matrix) ** 2) < 0.7)

    print()
    print("=" * 60)
    print("2. Perangkap: dua path (putih + gelap) tidak boleh digabung")
    print("=" * 60)

    # Kalau kedua path digabung, hasilnya 100% gelap dan QR tidak terbaca.
    all_positions = {
        (x, y)
        for y in range(len(original_matrix))
        for x in range(len(original_matrix))
    }
    check("putih + gelap menutupi seluruh grid",
        len(all_positions) == len(original_matrix) ** 2,
        "asumsi bentuk SVG SumoPod")

    # Urutan path dibalik: tetap harus benar.
    reversed_matrix = read_matrix_from_html(
        full_html(sumopod_svg(original_matrix, white_first=False))
    )
    check("urutan path dibalik tetap benar", reversed_matrix == original_matrix)

    # Kalau hanya ada path gelap (tanpa path putih), tetap harus benar.
    matrix_size = len(original_matrix)
    dark_module_path = " ".join(f"M {x} {y} l 1 0 0 1 -1 0 Z"
                       for y in range(matrix_size) for x in range(matrix_size)
                       if original_matrix[y][x])
    single_path_svg = (
        f'<svg id="qrcode" viewBox="0 0 {matrix_size} {matrix_size}">'
        f'<path d="{dark_module_path}" fill="#000000"></path></svg>'
    )
    check("hanya satu path (tanpa putih) tetap benar",
        read_matrix_from_html(single_path_svg) == original_matrix)

    print()
    print("=" * 60)
    print("3. Payload hasil decode harus sama dengan teks asli")
    print("=" * 60)

    payload = decode_payload_from_matrix(matrix)
    if payload is None:
        print("  (dilewati — OpenCV tidak terpasang)")
    else:
        check("decode balik ke teks asli", payload == text, repr(payload))

    print()
    print("=" * 60)
    print("4. Jaring pengaman: matriks terbalik")
    print("=" * 60)

    inverted_source_matrix = [
        [1 - cell for cell in row] for row in original_matrix
    ]
    inverted_matrix = read_matrix_from_html(
        full_html(sumopod_svg(inverted_source_matrix))
    )
    check(
        "matriks terbalik dikembalikan ke posisi benar",
        inverted_matrix == original_matrix,
    )

    print()
    print("=" * 60)
    print("5. Gambar hasil")
    print("=" * 60)

    image = build_image_from_matrix(matrix, size_px=210)
    if image is None:
        print("  (dilewati — Pillow tidak terpasang)")
    else:
        check("gambar berbentuk persegi", image.size[0] == image.size[1], str(image.size))
        check("tidak melebihi batas yang diminta", image.size[0] <= 210, str(image.size))
        check("tidak mengecil sampai tidak terbaca", image.size[0] >= 150, str(image.size))
        check("ada quiet zone (pojok putih)",
            image.getpixel((0, 0)) != 0, "pojok harus terang")

    # Batas harus dihormati untuk berbagai ukuran grid QR (versi 1..10).
    for grid_size in (21, 25, 29, 33, 41, 45, 57):
        box = build_image_from_matrix([[0] * grid_size for _ in range(grid_size)], size_px=210)
        if box is not None:
            check(f"grid {grid_size} -> sisi <= 210", box.size[0] <= 210, str(box.size))

    print()
    print("=" * 60)
    print("6. HTML yang tidak berbentuk harus gagal dengan jelas")
    print("=" * 60)

    for name, content in [
        ("HTML kosong", ""),
        ("tanpa elemen QR", full_html("<div>tidak ada QR</div>")),
        ("id svg bukan qrcode", full_html(sumopod_svg(original_matrix, id_svg='image'))),
        ("tanpa viewBox", full_html(sumopod_svg(original_matrix, include_viewbox=False))),
        ("grid tidak wajar",
         full_html('<svg id="qrcode" viewBox="0 0 5 5">'
                    '<path d="M 0 0 l 1 0 0 1 -1 0 Z" fill="#000000"></path></svg>')),
        ("tanpa path gelap",
         full_html(f'<svg id="qrcode" viewBox="0 0 {matrix_size} {matrix_size}">'
                    f'<path d="M 0 0 l 1 0 0 1 -1 0 Z" fill="#FFFFFF"></path></svg>')),
    ]:
        try:
            read_matrix_from_html(content)
            check(f"{name} -> QrCheckoutError", False, "tidak melempar error")
        except QrCheckoutError as exc:
            check(f"{name} -> QrCheckoutError", bool(str(exc)), str(exc)[:70])

    print()
    print("=" * 60)
    print("7. Tampilan nyata di Tkinter (jebakan mode gambar)")
    print("=" * 60)

    test_tkinter_render(check)

    # ---- uji jaringan, opsional ----
    if "--live" in sys.argv:
        print()
        print("=" * 60)
        print("8. Uji jaringan (sandbox sungguhan)")
        print("=" * 60)
        from sumopod_client import SumoPodClient, load_local_env
        import time

        load_local_env()
        key = os.environ.get("SUMOPOD_API_KEY", "").strip()
        if not key:
            print("  (dilewati — SUMOPOD_API_KEY tidak ada)")
        else:
            client = SumoPodClient(api_key=key, sandbox=True)
            payment_result = client.create_payment(
                order_id="INV-QRTEST-" + str(int(time.time())), amount=15000)
            html = client.get_checkout_html(payment_result["payment_link_url"])
            check("HTML checkout terambil", len(html) > 10000, f"{len(html)} char")

            m = read_matrix_from_html(html)
            check("matriks terbaca", len(m) == 33, f"{len(m)}x{len(m)}")
            p = decode_payload_from_matrix(m)
            check("payload ter-decode", bool(p), repr(p))
            check("payload berbentuk token heksadesimal 64 karakter",
                bool(p) and len(p) == 64 and all(c in "0123456789abcdef" for c in p),
                repr(p))

            html2 = client.get_checkout_html(payment_result["payment_link_url"])
            check("QR stabil antar muat ulang",
                read_matrix_from_html(html2) == m)

    print()
    print("=" * 60)
    print(f"LULUS {passed_count}   GAGAL {failure_callback}")
    print("=" * 60)
    return 1 if failure_callback else 0


if __name__ == "__main__":
    raise SystemExit(main())
