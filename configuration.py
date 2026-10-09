"""Pengaturan koneksi pembayaran dari environment atau file .env."""

import os

from sumopod_client import SumoPodClient, load_local_env


load_local_env()

API_KEY = os.environ.get("SUMOPOD_API_KEY", "").strip()
DEMO_MODE = os.environ.get("MODE_DEMO", "0").strip().lower() in (
    "1", "true", "yes", "on",
)
SANDBOX_MODE = os.environ.get("SUMOPOD_SANDBOX", "1").lower() not in (
    "0", "false", "no",
)
# Demo may use the provider's sandbox for QRIS practice, but never production.
LIVE_MODE = bool(API_KEY) and (not DEMO_MODE or SANDBOX_MODE)

SUMOPOD_CLIENT = (
    SumoPodClient(api_key=API_KEY, sandbox=SANDBOX_MODE)
    if LIVE_MODE else None
)
