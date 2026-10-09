"""Read the payment QR directly from SumoPod checkout HTML.

NO BROWSER, NO SERVER, NO WEBHOOK.
==================================
SumoPod's checkout page (https://sumo.sandbox.pymnt.global/payment-links/<id>)
is server-rendered HTML. The QR is already inside it, not drawn by JavaScript.
It looks like this:

    <svg id="qrcode" style="width:200px;height:200px;background:white"
         height="256" viewBox="0 0 33 33" width="256"
         xmlns="http://www.w3.org/2000/svg">
      <path d="M 7 0 l 1 0 0 1 -1 0 Z M 8 0 l 1 0 0 1 -1 0 Z ..." fill="#FFFFFF"></path>
      <path d="M 0 0 l 1 0 0 1 -1 0 Z M 1 0 l 1 0 0 1 -1 0 Z ..." fill="#000000"></path>
    </svg>

So the QR is an SVG full of 1x1 squares. viewBox="0 0 33 33" means a 33x33
module grid (QR version 4). Each subpath `M x y l 1 0 0 1 -1 0 Z` is ONE module
at column x, row y.

TRAPS ALREADY FOUND (do not repeat them):
----------------------------------------
1. There are TWO paths: one fill="#FFFFFF" (light modules, 546 of them) and one
   fill="#000000" (dark modules, 543). Together they are exactly 33x33 = 1089 —
   they tile the whole grid with no background. If you merge them, the matrix
   becomes 100% black and the QR is unreadable. DARK modules = the path whose
   fill is NOT white. That is the whole rule.

2. The QR is NOT a QRIS EMVCo string. Decoding it gives 64 hexadecimal
   characters (32 bytes), for example:
       dd9e26e517e68cf522509fa34f8e1b822f11e21df343bbffb639a781a9fe7c83
   The value is stable across page reloads and different for each payment. So it
   is a per-transaction token from SumoPod, not an EMVCo payload starting with
   "0002010102...".

3. No API endpoint returns that token. Already probed:
   /api/payment-links/{id}/qr, /qris, /qr-code, /checkout,
   /api/hosted-checkouts/{id}, /api/payins/{id}, /api/payins/{id}/qr, and their
   equivalents on the api-pay-sandbox host — all 404 (HTML) or
   "no Route matched with those values". The only source is the checkout HTML.

4. This page sits behind Cloudflare and rejects Python's User-Agent
   (HTTP 403 "error code: 1010"). A browser-like User-Agent is REQUIRED —
   SumoPodClient.get_checkout_html() already handles that.

THEREFORE: this module copies the module matrix verbatim from the HTML and
redraws it itself. No OpenCV, no decoding, no need to know what the token means.
What matters is that the QR shown matches the one on the page.

Decoding the payload (optional) uses cv2 if present; if not, it is skipped.

The QR is read from SumoPod checkout HTML and rendered locally. There is no
browser, server, webhook, or QR payload decoding required by the vending UI.
"""

from __future__ import annotations

import re

__all__ = [
    "QrCheckoutError",
    "read_matrix_from_html",
    "decode_payload_from_matrix",
    "build_image_from_matrix",
    "DEFAULT_QUIET_ZONE",
    "ESTIMATED_QUIET_ZONE",
]

# Quiet zone (white margin) added when drawing, in modules.
DEFAULT_QUIET_ZONE = 4
ESTIMATED_QUIET_ZONE = DEFAULT_QUIET_ZONE

# 7x7 QR finder pattern, used to make sure the matrix is not inverted.
_FINDER = (
    "1111111",
    "1000001",
    "1011101",
    "1011101",
    "1011101",
    "1000001",
    "1111111",
)


class QrCheckoutError(Exception):
    """The checkout HTML does not contain a readable QR."""


# ----------------------------------------------------------------------
# 1. Read the matrix from the HTML (pure stdlib, no dependencies)
# ----------------------------------------------------------------------
def _find_qr_svg(html):
    """Return the WHOLE <svg id="qrcode">...</svg> element, opening tag included.

    The opening tag must be included: the viewBox attribute (the grid size)
    lives there, not inside the element body.
    """
    match = re.search(r'<svg[^>]*\bid=["\']qrcode["\'][^>]*>', html)
    if not match:
        return None
    end = html.find("</svg>", match.end())
    if end < 0:
        return None
    return html[match.start():end]


def _modules_from_path(d_attr):
    """Turn a 'd' attribute into a set of dark (x, y) modules.

    The subpath shape SumoPod uses is `M x y l 1 0 0 1 -1 0 Z` (a 1x1 box).
    Only the starting point matters.
    """
    cells = set()
    for x, y in re.findall(r"M\s*([\d.+-]+)[\s,]+([\d.+-]+)", d_attr):
        try:
            cells.add((int(float(x)), int(float(y))))
        except ValueError:
            continue
    return cells


def _has_finder_patterns(matrix):
    """True if the three QR finder patterns are in place (matrix not inverted)."""
    n = len(matrix)
    if n < 21:
        return False

    def matches(row_start, col_start):
        for i in range(7):
            for j in range(7):
                if str(matrix[row_start + i][col_start + j]) != _FINDER[i][j]:
                    return False
        return True

    return (matches(0, 0) and matches(0, n - 7) and matches(n - 7, 0))


def read_matrix_from_html(html):
    """Read the QR module matrix from SumoPod's checkout HTML.

    Args:
        html: the checkout page contents (string).

    Returns:
        list[list[int]] of size N x N, 1 = dark module, 0 = light module.

    Raises:
        QrCheckoutError: if the QR element is missing or its contents make no sense.
    """
    if not html:
        raise QrCheckoutError("Empty HTML.")

    element = _find_qr_svg(html)
    if element is None:
        raise QrCheckoutError(
            'Could not find <svg id="qrcode"> in the HTML. '
            "The page may have changed shape, or the link is not a checkout page."
        )

    match = re.search(r'viewBox=["\']\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*["\']', element)
    if not match:
        raise QrCheckoutError("The QR element has no viewBox, so the grid size "
                              "is unknown.")
    width = int(round(float(match.group(1))))
    height = int(round(float(match.group(2))))
    if width != height or not 21 <= width <= 177:
        raise QrCheckoutError(f"Unreasonable QR grid size: {width}x{height}.")

    # Separate light and dark paths. This is the heart of trap number 1 above.
    light = set()
    dark = set()
    for tag in re.findall(r"<path[^>]*>", element):
        d = re.search(r'\bd=["\'](.*?)["\']', tag, re.S)
        if not d:
            continue
        colour = re.search(r'fill=["\']([^"\']*)["\']', tag)
        colour = colour.group(1).upper() if colour else ""
        cells = _modules_from_path(d.group(1))
        if colour in ("#FFFFFF", "#FFF", "WHITE"):
            light |= cells
        else:
            dark |= cells

    if not dark:
        raise QrCheckoutError("There are no dark paths inside the QR element.")

    matrix = [[0] * width for _ in range(width)]
    for x, y in dark:
        if 0 <= x < width and 0 <= y < width:
            matrix[y][x] = 1

    if light and dark & light:
        raise QrCheckoutError(
            f"Light and dark paths overlap on {len(dark & light)} modules — "
            "the colour split failed."
        )

    # Safety net: if the finder patterns are not where they belong, try inverting.
    if not _has_finder_patterns(matrix):
        inverted = [[1 - cell for cell in row] for row in matrix]
        if _has_finder_patterns(inverted):
            matrix = inverted

    return matrix


# ----------------------------------------------------------------------
# 2. Decode the payload (optional, needs cv2)
# ----------------------------------------------------------------------
def decode_payload_from_matrix(matrix, scale=12):
    """Decode the matrix into a payload string. Needs OpenCV; None if absent.

    The value is a 32-byte hexadecimal token, NOT a QRIS EMVCo string. See the
    notes in this module's docstring.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None

    n = len(matrix)
    qz = DEFAULT_QUIET_ZONE
    size = n + 2 * qz
    canvas = np.ones((size, size), dtype=np.uint8) * 255
    for y in range(n):
        for x in range(n):
            if matrix[y][x]:
                canvas[qz + y, qz + x] = 0
    pixels = cv2.resize(canvas, (size * scale, size * scale),
                        interpolation=cv2.INTER_NEAREST)

    data, _, _ = cv2.QRCodeDetector().detectAndDecode(pixels)
    return data or None


# ----------------------------------------------------------------------
# 3. Draw the matrix into an image (needs Pillow)
# ----------------------------------------------------------------------
def build_image_from_matrix(matrix, size_px=200, quiet_zone=DEFAULT_QUIET_ZONE):
    """Draw a QR matrix into a PIL.Image object.

    Modules are drawn as hard squares (no interpolation), so the result is as
    crisp as the QR on the page.

    Args:
        matrix: output of read_matrix_from_html().
        size_px: upper bound on the output side length. The actual side is
                 (N + 2*quiet_zone) * scale, where scale is the largest whole
                 number that does not exceed this value — so the result is
                 ALWAYS <= size_px.
        quiet_zone: white margin in modules. Do not use 0 — scanners need a margin.

    Returns:
        PIL.Image (mode "L"), or None if Pillow is not installed.

    MODE WARNING: the result is mode "L" (8-bit greyscale), NOT "1" (1-bit).
    Mode "1" is smaller and logically correct, BUT Tkinter misreads it:
    ImageTk.PhotoImage treats mode "1" as a paletted image with indices 0/1, and
    what appears on screen is a SOLID BLACK BOX. That bug has happened before —
    the QR "exists" but is invisible. Do not go back to mode "1" without
    checking how it renders in Tkinter.
    """
    try:
        from PIL import Image
    except ImportError:
        return None

    n = len(matrix)
    size = n + 2 * quiet_zone
    # Scale is rounded DOWN so the image side is guaranteed not to exceed
    # size_px. The QR holder in the panel is a fixed size, so an oversized image
    # would be cropped — and a cropped QR cannot be scanned.
    scale = max(1, int(size_px) // size)
    side = size * scale

    image = Image.new("L", (side, side), 255)   # 255 = white
    pixels = image.load()
    for y in range(n):
        row = matrix[y]
        for x in range(n):
            if not row[x]:
                continue
            x0 = (quiet_zone + x) * scale
            y0 = (quiet_zone + y) * scale
            for dy in range(scale):
                for dx in range(scale):
                    pixels[x0 + dx, y0 + dy] = 0
    return image


# ----------------------------------------------------------------------
# Demo CLI — prove it works without opening the application window
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import os
    import sys

    #     py qr_checkout.py                     -> create a sandbox payment
    #     py qr_checkout.py <payment_link_url>  -> reuse an existing link
    from sumopod_client import SumoPodClient, load_local_env

    load_local_env()
    key = os.environ.get("SUMOPOD_API_KEY", "").strip()
    if not key:
        raise SystemExit("No API key. Fill in .env or set SUMOPOD_API_KEY.")

    client = SumoPodClient(api_key=key, sandbox=True)

    if len(sys.argv) > 1:
        link = sys.argv[1]
    else:
        import time
        created = client.create_payment(
            order_id="INV-QRDEMO-" + str(int(time.time())), amount=15000)
        link = created["payment_link_url"]
        print("order_id :", created["order_id"])
        print("amount   :", created["amount"])

    print("link     :", link)

    html = client.get_checkout_html(link)
    print("HTML     :", len(html), "characters")

    matrix = read_matrix_from_html(html)
    n = len(matrix)
    dark = sum(sum(row) for row in matrix)
    print(f"matrix   : {n}x{n} modules, {dark} dark "
          f"({dark / (n * n) * 100:.1f}%)")

    payload = decode_payload_from_matrix(matrix)
    print("payload  :", payload)
    print("           (a hexadecimal token, NOT a QRIS EMVCo string)")

    output = "qr_checkout.png"
    image = build_image_from_matrix(matrix, size_px=410)
    if image is None:
        raise SystemExit("Pillow is not installed; cannot build the image.")
    image.convert("L").save(output)
    print("image    :", output, image.size)
