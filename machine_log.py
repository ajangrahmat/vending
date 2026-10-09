"""Pencatatan kejadian aplikasi ke machine_log.log."""

from datetime import datetime
import os


LOG_FILE = os.environ.get("VENDING_LOG") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "machine_log.log",
)


def log_event(message):
    """Tambahkan pesan bercap waktu; kegagalan menulis tidak menghentikan mesin."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as file:
            file.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {message}\n")
    except OSError:
        pass
