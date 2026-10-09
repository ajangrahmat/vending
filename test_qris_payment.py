"""Uji helper QRIS tanpa menghubungi SumoPod."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import qris_payment
from sumopod_client import SumoPodError


def test_fetch_checkout_qr():
    matrix = [[1, 0], [0, 1]]
    expected_image = object()
    requested_sizes = []
    original_reader = qris_payment.qr_checkout.read_matrix_from_html
    original_builder = qris_payment.qr_checkout.build_image_from_matrix
    qris_payment.qr_checkout.read_matrix_from_html = (
        lambda html: matrix if html == "<svg>checkout</svg>" else None
    )
    qris_payment.qr_checkout.build_image_from_matrix = (
        lambda value, size_px: requested_sizes.append(size_px) or expected_image
        if value == matrix else None
    )
    try:
        client = SimpleNamespace(
            get_checkout_html=lambda _link: "<svg>checkout</svg>"
        )
        image = qris_payment.fetch_checkout_qr(
            client, "https://example.test/payment-links/demo"
        )
    finally:
        qris_payment.qr_checkout.read_matrix_from_html = original_reader
        qris_payment.qr_checkout.build_image_from_matrix = original_builder

    assert image is expected_image
    assert requested_sizes == [qris_payment.QR_SIZE_PX]


def test_fetch_checkout_qr_retries_checkout_errors():
    call_count = 0
    original_sleep = qris_payment.time.sleep
    qris_payment.time.sleep = lambda _seconds: None

    def get_checkout_html(_link):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise SumoPodError("temporary checkout error")
        return "<svg>checkout</svg>"

    original_reader = qris_payment.qr_checkout.read_matrix_from_html
    original_builder = qris_payment.qr_checkout.build_image_from_matrix
    qris_payment.qr_checkout.read_matrix_from_html = lambda _html: [[1]]
    qris_payment.qr_checkout.build_image_from_matrix = (
        lambda _matrix, size_px: ("image", size_px)
    )
    try:
        client = SimpleNamespace(get_checkout_html=get_checkout_html)
        image = qris_payment.fetch_checkout_qr(
            client, "https://example.test/payment-links/demo", attempts=2
        )
    finally:
        qris_payment.time.sleep = original_sleep
        qris_payment.qr_checkout.read_matrix_from_html = original_reader
        qris_payment.qr_checkout.build_image_from_matrix = original_builder

    assert call_count == 2
    assert image == ("image", qris_payment.QR_SIZE_PX)


def test_expiration_helpers():
    expiration = datetime.now(timezone.utc) + timedelta(hours=1)
    parsed_expiration = qris_payment.parse_datetime(expiration.isoformat())

    assert parsed_expiration is not None
    assert parsed_expiration.tzinfo is not None
    assert qris_payment.parse_datetime("not a date") is None
    assert qris_payment.expiration_text(None) == ""
    assert qris_payment.expiration_text(parsed_expiration).startswith(
        " \u2022 QR berlaku sampai "
    )


if __name__ == "__main__":
    test_fetch_checkout_qr()
    test_fetch_checkout_qr_retries_checkout_errors()
    test_expiration_helpers()
    print("Semua uji helper QRIS lulus.")
