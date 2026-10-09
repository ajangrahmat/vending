"""Fungsi QRIS yang tidak bergantung pada widget tampilan."""

import re
import time
from datetime import datetime

import qr_checkout
from sumopod_client import SumoPodError


QR_SIZE_PX = 210


def fetch_checkout_qr(client, link, attempts=3):
    """Ambil QRIS asli dari halaman checkout dan kembalikan sebagai PIL.Image."""
    for attempt_index in range(attempts):
        try:
            html = client.get_checkout_html(link)
            matrix = qr_checkout.read_matrix_from_html(html)
        except (SumoPodError, qr_checkout.QrCheckoutError):
            if attempt_index < attempts - 1:
                time.sleep(1.5)
                continue
            return None

        image = qr_checkout.build_image_from_matrix(
            matrix, size_px=QR_SIZE_PX,
        )
        if image is not None:
            return image
        break
    return None


def parse_datetime(text):
    """Ubah waktu SumoPod menjadi datetime lokal."""
    if not text:
        return None
    clean_text = str(text).strip().replace("Z", "+00:00")
    clean_text = re.sub(r"\.(\d{6})\d+", r".\1", clean_text)
    try:
        return datetime.fromisoformat(clean_text).astimezone()
    except ValueError:
        return None


def expiration_text(expiration_time):
    """Bentuk keterangan masa berlaku QR untuk status pembayaran."""
    if expiration_time is None:
        return ""
    return " \u2022 QR berlaku sampai " + expiration_time.strftime("%H:%M")
