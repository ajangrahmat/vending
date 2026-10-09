"""SumoPod Payment Gateway client.

Uses only the standard library (urllib), no extra dependencies.

THE ACTUAL ENDPOINT MAP
=======================
Tested 2026-10-06 with a valid sandbox API key.

API host (needs X-Api-Key):
    POST /api/v1/payments            -> create a payment.  THE ONLY endpoint.
                                        GET/PUT/DELETE here are all 404.

Payment link host (PUBLIC, no API key):
    GET  /api/payment-links/{link_id} -> payment status.  <-- USED FOR POLLING

API host, public path (no key, returns HTML not JSON):
    GET  /api/v1/public/pay/{payment_id} -> human-readable "Payment Status" page.

Not in the API: fetch details by id, list payments, cancel a payment.
So the ONLY way to monitor status through the official API is a WEBHOOK.
But because the payment link host exposes a public status endpoint, polling
still works WITHOUT a server. That is what this module uses.

THE PAYMENT QR
==============
The QRIS code is NOT available from any API (thoroughly probed, all 404).
But it is already rendered inside the checkout page HTML as
<svg id="qrcode" viewBox="0 0 33 33">. Fetch that HTML with
get_checkout_html(), then read its module matrix with the qris module.
No browser or server is needed. The companion qr_checkout.py module reads
the QR directly from the checkout page.

IMPORTANT NOTES
---------------
1. The endpoints sit behind Cloudflare. Python's default User-Agent is blocked
   with HTTP 403 "error code: 1010". So ALWAYS send a browser-like User-Agent.
   Do not delete that line — without it everything fails.

2. `payment_id` != `link_id`.
   - payment_id : the UUID from create_payment()["payment_id"]
   - link_id    : the UUID inside create_payment()["payment_link_url"]
   Polling uses link_id. The extract_link_id() helper below pulls it out.

3. Validation rules that are confirmed:
   - expires_in_hours : a WHOLE number, 1..720. Cannot be under 1 hour.
   - order_id         : must be unique. Duplicate -> HTTP 409 ALREADY_EXISTS.
   - currency         : only "IDR".
   - amount           : a whole number, minimum 1.
   - payment_method_type_code : required if the merchant has more than one
     active method.

4. The sandbox fee measured 2.7% (15,000 -> fee 405). The documentation example
   shows 1.5%. Do not hardcode it — always read the `fee` field from the response.

This module is used directly by the vending application.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

__all__ = [
    "SumoPodClient",
    "SumoPodError",
    "load_local_env",
    "extract_link_id",
    "TERMINAL_STATUSES",
    "SANDBOX_BASE_URL",
    "PRODUCTION_BASE_URL",
]

SANDBOX_BASE_URL = "https://api-pay-sandbox.sumopod.com/api/v1"
PRODUCTION_BASE_URL = "https://api-pay.sumopod.com/api/v1"

# Final payment statuses. Once one of these appears, polling stops.
TERMINAL_STATUSES = frozenset({
    "SUCCESS", "COMPLETED", "PAID",
    "FAILED", "EXPIRED", "CANCELLED", "CANCELED",
})

# Statuses considered successful.
SUCCESS_STATUSES = frozenset({"SUCCESS", "COMPLETED", "PAID"})

# Link statuses meaning it can no longer be paid.
# WARNING: this is the LINK status, not the payment status.
LINK_DEAD_STATUSES = frozenset({"EXPIRED", "CANCELLED", "CANCELED", "INACTIVE"})

# What payin_status() returns when the payment has not started yet.
NOT_PAID_YET = "PENDING"

# Cloudflare rejects non-browser clients (error 1010). REQUIRED.
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)


def load_local_env(filename=".env", folder=None):
    """Read KEY=VALUE pairs from a .env file into os.environ.

    Environment variables that already exist are NOT overwritten, so
    `SUMOPOD_API_KEY=xxx py main.py` still wins over the .env contents. Setting
    the variable to an empty string also switches live mode off without deleting
    the .env file.

    Args:
        filename: file name, defaults to ".env".
        folder: folder to look in. Defaults to the project folder (the folder
            containing this module, which is the vending project folder.

    Returns:
        True if the file was found and read, False if it does not exist.
    """
    folder = folder or os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(folder, filename)
    if not os.path.exists(env_path):
        return False
    try:
        with open(env_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        return False
    return True


class SumoPodError(Exception):
    """An error from the API, from the payment link host, or from the network."""

    def __init__(self, message, status_code=None, code=None,
                 request_id=None, response_body=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.request_id = request_id
        self.response_body = response_body

    def __str__(self):
        bits = [self.message]
        if self.status_code is not None:
            bits.append(f"(HTTP {self.status_code})")
        if self.code:
            bits.append(f"code={self.code}")
        if self.request_id:
            bits.append(f"request_id={self.request_id}")
        return " ".join(bits)


def extract_link_id(payment_link_url):
    """Pull the link_id out of a payment_link_url.

    'https://sumo.sandbox.pymnt.global/payment-links/29e24cf2-...' -> '29e24cf2-...'
    """
    if not payment_link_url:
        raise ValueError("payment_link_url is empty")
    return payment_link_url.rstrip("/").rsplit("/", 1)[-1]


class SumoPodClient:
    """SumoPod client.

    Example:
        client = SumoPodClient(api_key="...", sandbox=True)
        created = client.create_payment(order_id="INV-001", amount=15000)
        print(created["payment_link_url"])
        result = client.wait_for_completion(created["payment_link_url"], timeout=900)
        if client.is_paid(result):
            dispense()
    """

    def __init__(self, api_key, base_url=None, sandbox=True, timeout=30):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = (base_url or
                         (SANDBOX_BASE_URL if sandbox else PRODUCTION_BASE_URL)).rstrip("/")
        self.timeout = timeout
        # The payment link host is not hardcoded: it is taken from the
        # payment_link_url returned by create_payment(), so it follows
        # sandbox/production automatically.
        self.link_host = None

    # ------------------------------------------------------------------
    # HTTP layer
    # ------------------------------------------------------------------
    def _request(self, method, url, payload=None, use_key=True):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None

        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", _BROWSER_UA)  # required: see the notes above
        if use_key:
            req.add_header("X-Api-Key", self.api_key)
        if data is not None:
            req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return json.loads(raw) if raw.strip() else {}

        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            body = {}
            try:
                body = json.loads(raw)
            except ValueError:
                pass

            message = body.get("error") or body.get("message") or f"HTTP {exc.code}"
            if exc.code == 401:
                message = ("API key rejected. Check the key and make sure "
                           "sandbox/production match.")
            elif exc.code == 403 and "1010" in raw:
                message = ("Blocked by Cloudflare (1010). The User-Agent is "
                           "missing or the IP is blocked.")
            elif exc.code == 409:
                message = "order_id already used. Use a different order_id."
            elif exc.code == 404 and "page not found" in raw:
                message = f"Endpoint does not exist: {method} {url}"

            raise SumoPodError(
                message,
                status_code=exc.code,
                code=body.get("code"),
                request_id=body.get("request_id"),
                response_body=body or raw,
            ) from exc

        except urllib.error.URLError as exc:
            raise SumoPodError(f"Could not connect to {url}: {exc.reason}") from exc

    # ------------------------------------------------------------------
    # Creating a payment
    # ------------------------------------------------------------------
    def create_payment(
        self,
        order_id,
        amount,
        currency="IDR",
        expires_in_hours=1,
        success_return_url=None,
        cancel_return_url=None,
        payment_method_type_code="QRIS",
    ):
        """Create a new payment.

        Returns the API response dict. The fields that actually exist:

            payment_id, order_id, amount, fee, net_amount, currency,
            payment_link_url, status ("pending"), expires_at, created_at

        Note: `created_at` can be null — do not rely on it.

        Raises:
            SumoPodError: 409 if the order_id has already been used.
        """
        payload = {
            "order_id": order_id,
            "amount": int(amount),
            "currency": currency,
            "expires_in_hours": int(expires_in_hours),
            "payment_method_type_code": payment_method_type_code,
        }
        if success_return_url:
            payload["success_return_url"] = success_return_url
        if cancel_return_url:
            payload["cancel_return_url"] = cancel_return_url

        result = self._request("POST", f"{self.base_url}/payments", payload)

        # Remember the payment link host so get_status() can be used without
        # passing the host explicitly.
        link = (result or {}).get("payment_link_url")
        if link:
            self.link_host = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(link))

        return result

    # ------------------------------------------------------------------
    # Monitoring status — via the payment link host, WITHOUT an API key
    # ------------------------------------------------------------------
    def get_payment_link(self, link_id_or_url):
        """Fetch the payment status from the payment link host (public).

        The argument may be just the link_id or the full payment_link_url.

        Example response:
            {
              "status": "ACTIVE",
              "amount": "15000",
              "customerReference": "INV-TEST-001",
              "payinIds": [
                {"id": "payin-...", "status": "PENDING", "paymentChannel": "QRIS"}
              ],
              "expiredTime": "2026-10-06T15:21:23.409Z"
            }
        """
        if link_id_or_url.startswith("http"):
            parsed = urllib.parse.urlparse(link_id_or_url)
            host = f"{parsed.scheme}://{parsed.netloc}"
            link_id = extract_link_id(link_id_or_url)
        else:
            if not self.link_host:
                raise SumoPodError(
                    "Payment link host is unknown. Call create_payment() first, "
                    "or pass the full payment_link_url."
                )
            host = self.link_host
            link_id = link_id_or_url

        return self._request("GET", f"{host}/api/payment-links/{link_id}", use_key=False)

    def get_checkout_html(self, payment_link_url, timeout=None):
        """Fetch the checkout page HTML (public, no API key).

        The payment QR is already rendered inside this HTML as
        <svg id="qrcode">. Use qris.read_matrix_from_html() to read it. No
        browser needed, no server needed.

        Args:
            payment_link_url: the payment_link_url value from create_payment().
            timeout: override the client timeout.

        Returns:
            str: the page contents.

        Raises:
            SumoPodError: if the page cannot be fetched.
        """
        if not payment_link_url:
            raise ValueError("payment_link_url is empty")

        req = urllib.request.Request(payment_link_url)
        req.add_header("User-Agent", _BROWSER_UA)   # required: Cloudflare 1010
        req.add_header("Accept", "text/html,application/xhtml+xml")

        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            raise SumoPodError(
                f"The checkout page could not be opened (HTTP {exc.code}).",
                status_code=exc.code,
            ) from exc
        except urllib.error.URLError as exc:
            raise SumoPodError(
                f"Could not connect to the checkout page: {exc.reason}"
            ) from exc

    @staticmethod
    def payin_status(detail):
        """Get the PAYMENT status out of a get_payment_link() response.

        The payment status lives in payinIds[0].status (PENDING / SUCCESS / FAILED / ...).

        Careful: on a freshly created link, `payinIds` does not exist yet at all.
        At that moment detail["status"] holds "ACTIVE" — and that is the LINK
        status, not the payment status. Do not confuse the two. When there is no
        payin yet we report NOT_PAID_YET ("PENDING"), unless the link is already dead.
        """
        if not isinstance(detail, dict):
            return None

        payin = detail.get("payinIds") or []
        if payin and isinstance(payin[0], dict) and payin[0].get("status"):
            return payin[0]["status"]

        link_status = (detail.get("status") or "").upper()
        if link_status in LINK_DEAD_STATUSES:
            return link_status

        return NOT_PAID_YET

    @staticmethod
    def link_status(detail):
        """LINK status (ACTIVE / EXPIRED / ...). Not the payment status."""
        return (detail or {}).get("status") if isinstance(detail, dict) else None

    @classmethod
    def is_paid(cls, detail):
        """True if the payment has already succeeded."""
        return cls.payin_status(detail) in SUCCESS_STATUSES

    def wait_for_completion(
        self,
        link_id_or_url,
        timeout=900,
        interval=3.0,
        on_tick=None,
        should_stop=None,
    ):
        """Poll the status until it is final or the timeout hits.

        Args:
            link_id_or_url: the payment_link_url from create_payment(), or its link_id.
            timeout: total seconds. Default 900 (15 minutes).
                     Remember the QR lives at least 1 hour, so take that into account.
            interval: seconds between polls.
            on_tick: callable(status: str|None) -> None, called on every poll.
                     Use it to refresh a status label in the GUI.
            should_stop: callable() -> bool. If True, stop early.
                         Use it so the user can cancel.

        Returns:
            The last detail dict.

        Raises:
            SumoPodError: if the timeout hits before a final status.
        """
        deadline = time.monotonic() + timeout
        last = {}

        while True:
            if should_stop is not None and should_stop():
                return last

            last = self.get_payment_link(link_id_or_url)
            status = self.payin_status(last)

            if on_tick is not None:
                on_tick(status)

            if status in TERMINAL_STATUSES:
                return last

            if time.monotonic() >= deadline:
                raise SumoPodError(
                    f"Timeout waiting for payment (last status: {status!r}, "
                    f"{timeout}s). The payment was NOT cancelled — the link is "
                    f"still live until expires_at."
                )

            time.sleep(interval)


if __name__ == "__main__":
    load_local_env()

    key = os.environ.get("SUMOPOD_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "No API key yet. Fill in the .env file (see .env.example), or set "
            "the SUMOPOD_API_KEY environment variable."
        )

    client = SumoPodClient(api_key=key, sandbox=True)
    created = client.create_payment(order_id="INV-DEMO-001", amount=15000)
    print("payment_id       :", created.get("payment_id"))
    print("payment_link_url :", created.get("payment_link_url"))
    print("fee              :", created.get("fee"),
          "| net:", created.get("net_amount"))
    print("\nWaiting for payment (polling the payment link host, no webhook)...")
    result = client.wait_for_completion(
        created["payment_link_url"],
        timeout=900,
        interval=3.0,
        on_tick=lambda s: print("  status:", s),
    )
    print("\nDone:", client.payin_status(result))
