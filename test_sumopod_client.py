"""
test_sumopod_client.py — Uji sumopod_client.py lewat server tiruan lokal.

Server tiruan ini meniru perilaku yang SUDAH DIVERIFIKASI dari sandbox SumoPod
(2026-10-06), termasuk bentuk respons dan kode error yang sebenarnya:

  - POST /api/v1/payments                  -> butuh X-Api-Key
  - GET  /api/payment-links/{link_id}      -> publik, tanpa key
  - 401 {"message":"Unauthorized"} kalau key salah
  - 409 {"error":"order_id already exists","code":"ALREADY_EXISTS"}
  - 400 {"error":"expires_in_hours must be between 1 and 720 hours from now"}
  - 404 {"code":"DATA_NOT_FOUND"} untuk link_id asing

Jalankan:  py test_sumopod_client.py
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sumopod_client import (
    SumoPodClient,
    SumoPodError,
    extract_link_id,
    load_local_env,
)

MOCK_KEY = "test_key_123"


class MockSumoPod(BaseHTTPRequestHandler):
    """Satu server meniru dua host: host API dan host payment link."""

    payments: dict = {}      # payment_id -> respons create
    links: dict = {}         # link_id    -> status link (termasuk ambang & jumlah polling)
    order_ids: set = set()

    def log_message(self, *args):
        pass

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parts(self):
        return [p for p in self.path.split("?")[0].split("/") if p]

    # ---------------- POST: hanya membuat pembayaran ----------------
    def do_POST(self):
        if self.path.split("?")[0] != "/api/v1/payments":
            return self._send(404, {"message": "no Route matched with those values"})

        if self.headers.get("X-Api-Key") != MOCK_KEY:
            return self._send(401, {"message": "Unauthorized", "request_id": uuid.uuid4().hex})

        n = int(self.headers.get("Content-Length") or 0)
        data = json.loads(self.rfile.read(n) or b"{}")

        if not data.get("payment_method_type_code"):
            return self._send(400, {"error": "multiple payment methods are active for this "
                                             "merchant; specify payment_method_type_code",
                                    "code": "BAD_REQUEST"})

        expires_in_hours = data.get("expires_in_hours", 1)
        if not isinstance(expires_in_hours, int) or not (1 <= expires_in_hours <= 720):
            return self._send(400, {"error": "expires_in_hours must be between 1 and 720 "
                                             "hours from now", "code": "INVALID_INPUT"})

        if int(data.get("amount", 0)) < 1:
            return self._send(400, {"error": "Invalid request body", "code": "INVALID_REQUEST"})

        if data.get("order_id") in self.order_ids:
            return self._send(409, {"error": "order_id already exists", "code": "ALREADY_EXISTS"})
        self.order_ids.add(data.get("order_id"))

        pid = str(uuid.uuid4())
        link_id = str(uuid.uuid4())
        amount = int(data["amount"])
        fee = int(round(amount * 0.027))   # tarif sandbox terukur 2,7%

        host = f"http://127.0.0.1:{self.server.server_address[1]}"
        response = {
            "payment_id": pid,
            "order_id": data["order_id"],
            "amount": amount,
            "fee": fee,
            "net_amount": amount - fee,
            "currency": "IDR",
            "payment_link_url": f"{host}/payment-links/{link_id}",
            "status": "pending",
            "expires_at": "2026-10-06T15:21:23.409587159Z",
            "created_at": None,
        }
        self.payments[pid] = response
        self.links[link_id] = {"amount": str(amount),
                               "customerReference": data["order_id"],
                               "status": "ACTIVE", "payin": "PENDING",
                               "polls": 0, 'succeed_after': 3}
        return self._send(201, response)

    # ---------------- GET: hanya status payment link ----------------
    def do_GET(self):
        parts = self._parts()
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "payment-links":
            link_id = parts[2]
            if link_id not in self.links:
                return self._send(404, {"code": "DATA_NOT_FOUND",
                                        "message": "data not found in our system"})
            # tanpa cek API key — endpoint ini memang publik
            status_data = self.links[link_id]
            status_data["polls"] += 1
            if status_data["polls"] >= status_data['succeed_after'] and status_data["payin"] == "PENDING":
                status_data["payin"] = "SUCCESS"
            response = {
                "id": f"plr-{link_id[:8]}",
                "merchantId": "mc-mock",
                "status": status_data["status"],
                "amount": status_data["amount"],
                "currency": "IDR",
                "expiredTime": "2026-10-06T15:21:23.409Z",
                "customerReference": status_data["customerReference"],
            }
            # tirukan link yang baru dibuat: payinIds belum ada sama sekali
            if status_data["payin"] is not None:
                response["payinIds"] = [{"id": f"payin-{link_id[:8]}",
                                        "status": status_data["payin"],
                                        "paymentChannel": "QRIS"}]
            return self._send(200, response)

        return self._send(404, {"message": "no Route matched with those values"})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), MockSumoPod)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    client = SumoPodClient(api_key=MOCK_KEY,
                           base_url=f"http://127.0.0.1:{port}/api/v1", timeout=10)

    passed_count = failure_callback = 0

    def check(name, condition, info=""):
        nonlocal passed_count, failure_callback
        if condition:
            passed_count += 1
            print(f"  [OK]    {name}")
        else:
            failure_callback += 1
            print(f"  [GAGAL] {name}  {info}")

    print("\n== 0. load_local_env ==")
    with tempfile.TemporaryDirectory(prefix="sumopod_env_test_") as temp_folder:
        env_path = os.path.join(temp_folder, "test.env")
        variable_name = "SUMOPOD_TEST_ENV_VALUE"
        os.environ.pop(variable_name, None)
        with open(env_path, "w", encoding="utf-8") as env_file:
            env_file.write("# local test setting\n")
            env_file.write(f'{variable_name}="loaded value"\n')
        check("environment file loads", load_local_env("test.env", temp_folder))
        check(
            "environment value loads without qrispy package",
            os.environ.get(variable_name) == "loaded value",
            os.environ.get(variable_name),
        )
        os.environ[variable_name] = "existing value"
        with open(env_path, "w", encoding="utf-8") as env_file:
            env_file.write(f"{variable_name}=new value\n")
        load_local_env("test.env", temp_folder)
        check(
            "existing environment value is preserved",
            os.environ.get(variable_name) == "existing value",
            os.environ.get(variable_name),
        )
        os.environ.pop(variable_name, None)

    print("\n== 1. create_payment ==")
    b = client.create_payment(order_id="INV-001", amount=15000)
    check("payment_id ada", bool(b.get("payment_id")))
    check("status 'pending'", b.get("status") == "pending", b.get("status"))
    check("payment_link_url terisi", "/payment-links/" in b.get("payment_link_url", ""))
    check("fee 2,7% dari 15.000 = 405", b.get("fee") == 405, b.get("fee"))
    check("net_amount = 14.595", b.get("net_amount") == 14595, b.get("net_amount"))
    check("link_host terdeteksi dari respons", client.link_host == f"http://127.0.0.1:{port}",
        client.link_host)

    print("\n== 2. ambil_link_id ==")
    check("ekstrak UUID dari URL",
        extract_link_id("https://x.y/payment-links/abc-123") == "abc-123")

    print("\n== 3. get_payment_link (tanpa API key) ==")
    d = client.get_payment_link(b["payment_link_url"])
    check("status_payin() -> PENDING", client.payin_status(d) == "PENDING",
        client.payin_status(d))
    check("sukses() False saat PENDING", client.is_paid(d) is False)

    print("\n== 4. wait_for_completion (polling, tanpa webhook) ==")
    trace = []
    result = client.wait_for_completion(b["payment_link_url"], timeout=20, interval=0.2,
                                       on_tick=lambda s: trace.append(s))
    check("status akhir SUCCESS", client.payin_status(result) == "SUCCESS",
        client.payin_status(result))
    check("sukses() True", client.is_paid(result) is True)
    check("on_tick terpanggil >= 2x", len(trace) >= 2, trace)

    print("\n== 5. should_stop (user menekan batal) ==")
    b2 = client.create_payment(order_id="INV-002", amount=5000)
    # pastikan link ini TIDAK pernah jadi SUCCESS, supaya bisa diuji berhenti & timeout
    MockSumoPod.links[extract_link_id(b2["payment_link_url"])]['succeed_after'] = 10 ** 9
    stopped = {"n": 0}
    def stop():
        stopped["n"] += 1
        return stopped["n"] > 2

    result_2 = client.wait_for_completion(b2["payment_link_url"], timeout=20, interval=0.1,
                                        should_stop=stop)
    check("berhenti atas permintaan", client.payin_status(result_2) == "PENDING",
        client.payin_status(result_2))

    print("\n== 6. Link baru: payinIds belum ada (kasus nyata di sandbox) ==")
    b3 = client.create_payment(order_id="INV-003", amount=7000)
    MockSumoPod.links[extract_link_id(b3["payment_link_url"])]["payin"] = None
    d3 = client.get_payment_link(b3["payment_link_url"])
    check("payinIds memang tidak dikirim", "payinIds" not in d3, list(d3.keys()))
    check("status_link() -> ACTIVE", client.link_status(d3) == "ACTIVE", client.link_status(d3))
    check("status_payin() -> PENDING (bukan ACTIVE)",
        client.payin_status(d3) == "PENDING", client.payin_status(d3))
    check("sukses() False", client.is_paid(d3) is False)

    print("\n== 7. Validasi input ==")
    def tolak(name, kwargs, code):
        try:
            client.create_payment(**kwargs)
            check(name, False, "tidak melempar error")
        except SumoPodError as e:
            check(name, e.status_code == code, f"dapat {e.status_code}")

    tolak("order_id duplikat -> 409",
          dict(order_id="INV-001", amount=1000), 409)
    tolak("expires_in_hours=0 -> 400",
          dict(order_id="INV-900", amount=1000, expires_in_hours=0), 400)
    tolak("expires_in_hours=0.5 -> 400",
          dict(order_id="INV-901", amount=1000, expires_in_hours=0.5), 400)
    tolak("expires_in_hours=721 -> 400",
          dict(order_id="INV-902", amount=1000, expires_in_hours=721), 400)
    tolak("amount=0 -> 400",
          dict(order_id="INV-903", amount=0), 400)
    tolak("tanpa method code -> 400",
          dict(order_id="INV-904", amount=1000, payment_method_type_code=None), 400)

    print("\n== 8. Penanganan error ==")
    incorrect = SumoPodClient(api_key="key_palsu",
                          base_url=f"http://127.0.0.1:{port}/api/v1", timeout=10)
    try:
        incorrect.create_payment(order_id="INV-905", amount=1000)
        check("key salah -> SumoPodError 401", False, "tidak melempar error")
    except SumoPodError as e:
        check("key salah -> SumoPodError 401", e.status_code == 401, str(e))
        check("request_id terbaca", bool(e.request_id))

    try:
        client.get_payment_link("link-id-tidak-ada")
        check("link asing -> 404", False, "tidak melempar error")
    except SumoPodError as e:
        check("link asing -> 404", e.status_code == 404, str(e))
        check("code DATA_NOT_FOUND terbaca", e.code == "DATA_NOT_FOUND", e.code)

    try:
        client.wait_for_completion(b2["payment_link_url"], timeout=0.5, interval=0.1)
        check("timeout melempar error", False, "tidak melempar error")
    except SumoPodError as e:
        check("timeout melempar error", "Timeout" in str(e), str(e))

    server.shutdown()

    print(f"\n{'=' * 46}")
    print(f"LULUS {passed_count}   GAGAL {failure_callback}")
    print("=" * 46)
    return 1 if failure_callback else 0


if __name__ == "__main__":
    raise SystemExit(main())
