"""
test_main_gui.py — Uji wiring pembayaran di main.py tanpa membuka jendela.

main.py memanggil root.mainloop() di baris terakhir, jadi tidak bisa diimpor
langsung. Skrip ini mengganti mainloop dengan urutan pemeriksaan: jendela tetap
dibuat dan seluruh widget nyata, tapi alih-alih menunggu, kita jalankan
skenario lalu periksa hasilnya.

Dua mode lokal dan dua mode demo diuji, masing-masing di proses terpisah:

  py test_main_gui.py                 # uji simulasi dan demo lokal/sandbox
  py test_main_gui.py --live           # uji live sungguhan (membuat transaksi)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import tkinter
from types import SimpleNamespace

import qris_payment

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="backslashreplace")

SRC = "main.py"


def _has_api_key():
    """Cek ada-tidaknya API key, dari environment variable atau file .env."""
    if os.environ.get("SUMOPOD_API_KEY", "").strip():
        return True
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path, encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line.startswith("SUMOPOD_API_KEY="):
                    return bool(line.split("=", 1)[1].strip().strip('"').strip("'"))
    except OSError:
        pass
    return False


def _run_child(mode):
    """Dijalankan di proses anak: exec main.py dengan mainloop dipatch."""
    ns = {}
    result = {'checks': [], 'error': None, "info": []}

    def check(name, condition, info=""):
        result['checks'].append((name, bool(condition), info))

    original_mainloop = tkinter.Tk.mainloop

    def fake_mainloop(self):
        try:
            self.withdraw()          # jangan tampilkan jendela saat uji
            smoke(self)
        except Exception:
            import traceback
            result['error'] = traceback.format_exc()
        finally:
            try:
                self.destroy()
            except Exception:
                pass

    def pump(root, seconds):
        """Proses event selama `detik` detik tanpa memblokir."""
        end_time = time.monotonic() + seconds
        while time.monotonic() < end_time:
            root.update()
            time.sleep(0.02)

    def smoke(root):
        root.update()

        check("6 kartu produk dibuat", len(ns["ui"]['product_cards']) == 6, len(ns["ui"]['product_cards']))
        check(
            "semua gambar produk dimuat dari assets",
            len(ns["ui"]['product_image_labels']) == 6
            and all(label.cget("image") for label in ns["ui"]['product_image_labels'])
            and len(ns["ui"]['image_references']) == 6,
            len(ns["ui"]['image_references']),
        )
        check("total awal Rp 0", ns["ui"]['total_label']["text"] == "Rp 0",
            ns["ui"]['total_label']["text"])
        check("tombol batal tersembunyi",
            ns["ui"]['cancel_button'].winfo_manager() == "", ns["ui"]['cancel_button'].winfo_manager())
        check("panel QR kosong sebelum transaksi (tidak ada gambar)",
            ns["ui"]['qr_label'].image is None, bool(ns["ui"]['qr_label'].image))
        check("label QR tidak dipasang sebelum transaksi",
            ns["ui"]['qr_label'].winfo_manager() == "", ns["ui"]['qr_label'].winfo_manager())
        check("placeholder QR tampil",
            ns["ui"]["qr_state"]["placeholder"] is not None
            and ns["ui"]["qr_state"]["placeholder"].winfo_manager() == "pack",
            ns["ui"]["qr_state"]["placeholder"].winfo_manager()
            if ns["ui"]["qr_state"]["placeholder"] else None)
        check("qris.png tidak dipakai lagi", "QR_AWAL" not in ns)
        check("tombol browser sudah dihapus", "btn_buka" not in ns)
        check("mode terdeteksi benar",
            ns['LIVE_MODE'] == (mode in ("live", "demo-sandbox")),
            ns['LIVE_MODE'])
        check("mode demo terdeteksi benar",
            ns['DEMO_MODE'] == mode.startswith("demo"), ns['DEMO_MODE'])
        if mode == "demo":
            check("mode demo menonaktifkan klien pembayaran live",
                ns["client"] is None)
            check("mode demo ditampilkan pada tombol bayar",
                ns["ui"]['pay_button']["text"] == "BAYAR (SIMULASI DEMO)",
                ns["ui"]['pay_button']["text"])
        if mode == "demo-sandbox":
            check("mode demo sandbox memakai endpoint sandbox",
                ns["client"] is not None
                and "sandbox" in ns["client"].base_url,
                getattr(ns["client"], "base_url", None))
            check("tombol bayar menjelaskan pembayaran sandbox",
                ns["ui"]['pay_button']["text"] == "BAYAR QRIS (SANDBOX)",
                ns["ui"]['pay_button']["text"])
        if mode == "live":
            check(
                "pembayaran live diblokir tanpa Arduino siap",
                ns["ui"]['pay_button']["state"] == "disabled",
                ns["ui"]['pay_button']["state"],
            )

        # --- stok persisten ---
        # Berkas stok sementara sengaja diisi {"Air Mineral": 5} oleh proses
        # induk, jadi kalau pemuatan gagal nilainya tetap 15 (nilai bawaan).
        check("stok tersimpan dimuat dari berkas",
            ns['products'][0]['stock'] == 5, ns['products'][0]['stock'])
        check("produk lain memakai nilai bawaan",
            ns['products'][1]['stock'] == 12, ns['products'][1]['stock'])

        ns['reset_stock']()
        root.update()
        check("reset stok mengembalikan semua ke nilai awal",
            [p['stock'] for p in ns['products']] == [p['initial_stock'] for p in ns['products']],
            [p['stock'] for p in ns['products']])
        check("berkas stok benar-benar ditulis",
            os.path.exists(ns['STOCK_FILE']), ns['STOCK_FILE'])
        # Penulisan stok harus atomik: tulis ke .tmp lalu os.replace(). Kalau
        # berkas sementara tertinggal, berarti penggantiannya gagal di tengah.
        check("penulisan stok tidak meninggalkan berkas sementara",
            not os.path.exists(ns['STOCK_FILE'] + ".tmp"),
            ns['STOCK_FILE'] + ".tmp")

        # --- catatan mesin ---
        # Mesin jalan tanpa diawasi, jadi harus ada jejak yang bisa diperiksa.
        log_content = ""
        try:
            with open(os.environ["VENDING_LOG"], encoding="utf-8") as file:
                log_content = file.read()
        except OSError:
            pass
        check("catatan mesin ditulis", os.path.exists(os.environ["VENDING_LOG"]), os.environ["VENDING_LOG"])
        check("catatan mesin menandai mesin dijalankan",
            "mesin dijalankan" in log_content, log_content[:120])

        # --- keranjang kosong: tombol bayar harus mati ---
        check("tombol bayar mati saat keranjang kosong",
            ns["ui"]['pay_button']["state"] == "disabled", ns["ui"]['pay_button']["state"])

        # --- tambah, kurangi, kosongkan ---
        ns['select_product'](0)   # Air Mineral 3.000
        root.update()
        check("tambah: total Rp 3.000", ns['order_data']['total_amount'] == 3000, ns['order_data']['total_amount'])
        check(
            "tombol bayar mengikuti kesiapan Arduino",
            ns["ui"]['pay_button']["state"]
            == ("disabled" if mode == "live" else "normal"),
            ns["ui"]['pay_button']["state"],
        )
        check("tambah: ada pemberitahuan",
            "ditambahkan" in ns['notification_label']["text"], ns['notification_label']["text"])

        ns['select_product'](1)   # Kopi 5.000
        root.update()
        check("tambah 2 produk: total Rp 8.000", ns['order_data']['total_amount'] == 8000, ns['order_data']['total_amount'])

        ns['remove_order_item']("Kopi")
        root.update()
        check("kurangi: total kembali Rp 3.000", ns['order_data']['total_amount'] == 3000, ns['order_data']['total_amount'])
        check("kurangi: stok Kopi kembali 12", ns['products'][1]['stock'] == 12,
            ns['products'][1]['stock'])
        check("kurangi: Kopi keluar dari pesanan", "Kopi" not in ns['order_data']['items'],
            ns['order_data']['items'])

        # kurangi barang yang tidak ada di pesanan harus diabaikan diam-diam
        ns['remove_order_item']("Cokelat")
        root.update()
        check("kurangi barang asing tidak mengubah total", ns['order_data']['total_amount'] == 3000,
            ns['order_data']['total_amount'])

        ns['select_product'](2)   # Teh Botol 4.000
        root.update()
        ns['clear_order']()
        root.update()
        check("kosongkan: pesanan kosong", ns['order_data']['items'] == [], ns['order_data']['items'])
        check("kosongkan: total 0", ns['order_data']['total_amount'] == 0, ns['order_data']['total_amount'])
        check("kosongkan: semua stok kembali seperti semula",
            [p['stock'] for p in ns['products']] == [p['initial_stock'] for p in ns['products']],
            [p['stock'] for p in ns['products']])
        check("kosongkan: tombol bayar mati lagi",
            ns["ui"]['pay_button']["state"] == "disabled", ns["ui"]['pay_button']["state"])

        # --- pilih produk ---
        ns['select_product'](0)   # Air Mineral 3.000
        root.update()
        check("total jadi Rp 3.000", ns["ui"]['total_label']["text"] == "Rp 3.000",
            ns["ui"]['total_label']["text"])
        check("stok berkurang jadi 14", ns['products'][0]['stock'] == 14,
            ns['products'][0]['stock'])
        if mode in ("demo", "demo-sandbox"):
            check("mode demo mengizinkan bayar tanpa Arduino",
                ns["ui"]['pay_button']["state"] == "normal"
                and ns["dispenser_ready"] is False,
                (ns["ui"]['pay_button']["state"], ns["dispenser_ready"]))

        # --- mulai bayar ---
        sandbox_payment_calls = []
        if mode == "demo-sandbox":
            def sandbox_payment_stub():
                sandbox_payment_calls.append(True)
                if len(sandbox_payment_calls) == 1:
                    ns["post_to_ui"](ns["dispense_product"])

            ns["run_live_payment"] = sandbox_payment_stub
            ns["serial_controller"].check_ready = lambda: (
                (_ for _ in ()).throw(AssertionError("Arduino harus dilewati"))
            )
        if mode == "live":
            # Pemeriksaan alur pembayaran memakai status Arduino tiruan agar
            # tes tidak membuka koneksi ke perangkat fisik.
            ns["dispenser_ready"] = True
            ns["serial_controller"].check_ready = lambda: None
            ns["update_order"]()
        ns['start_qris_payment']()
        root.update()
        check("sedang_bayar True", ns['order_data']['payment_in_progress'] is True)
        check("tombol bayar dinonaktifkan", ns["ui"]['pay_button']["state"] == "disabled",
            ns["ui"]['pay_button']["state"])
        check("tombol batal muncul", ns["ui"]['cancel_button'].winfo_manager() == "pack",
            ns["ui"]['cancel_button'].winfo_manager())

        # produk tidak boleh bisa ditambah saat pembayaran berjalan
        ns['select_product'](1)
        root.update()
        check("produk terkunci saat bayar", ns["ui"]['total_label']["text"] == "Rp 3.000",
            ns["ui"]['total_label']["text"])

        if mode == "live":
            # tunggu worker thread selesai membuat pembayaran
            deadline = time.monotonic() + 45
            while ns['order_data']['payment_link'] is None and time.monotonic() < deadline:
                root.update()
                time.sleep(0.05)
                if ns["ui"]['pay_button']["state"] == "normal" and not ns['order_data']['payment_in_progress']:
                    break     # gagal lebih awal

            pump(root, 1.5)   # beri waktu pump memasang QR & tombol ke widget

            # QR asli diambil dari halaman checkout lewat jaringan, jadi tunggu
            # sampai label-nya berubah — entah jadi QR asli atau jadi cadangan.
            deadline = time.monotonic() + 30
            while (ns["ui"]['scan_label']["text"] not in ("Scan QRIS untuk membayar",
                                                    "Scan untuk membuka halaman pembayaran")
                   and time.monotonic() < deadline):
                root.update()
                time.sleep(0.05)
            pump(root, 0.5)

            result["info"].append("link_bayar = %r" % (ns['order_data']['payment_link'],))
            check("payment_link_url didapat", isinstance(ns['order_data']['payment_link'], str)
                and "/payment-links/" in ns['order_data']['payment_link'], ns['order_data']['payment_link'])
            check("QR asli dari halaman checkout tampil (bukan cadangan link)",
                ns["ui"]['scan_label']["text"] == "Scan QRIS untuk membayar",
                ns["ui"]['scan_label']["text"])
            check("QR terpasang (ada gambarnya)",
                ns["ui"]['qr_label'].image is not None, bool(ns["ui"]['qr_label'].image))
            check("label QR dipasang menggantikan placeholder",
                ns["ui"]['qr_label'].winfo_manager() == "pack", ns["ui"]['qr_label'].winfo_manager())
            check("placeholder disembunyikan saat QR tampil",
                ns["ui"]["qr_state"]["placeholder"].winfo_manager() == "",
                ns["ui"]["qr_state"]["placeholder"].winfo_manager())

            # ambil ulang QR langsung dari fungsinya, untuk memastikan hasilnya
            # benar-benar ada dan tidak melebihi wadah (QR terpotong = gagal pindai)
            image = qris_payment.fetch_checkout_qr(
                ns['client'], ns['order_data']['payment_link'])
            check("QR asli bisa diambil ulang", image is not None)
            check("QR muat di wadah (<= 210 px)",
                image is not None and image.size[0] <= 210,
                str(getattr(image, "size", None)))

            pump(root, 8)     # beri waktu beberapa kali polling
            text = ns["ui"]['payment_status_label']["text"]
            result["info"].append("status = %r" % text)
            check("status menyebut menunggu", "Menunggu pembayaran" in text, text)
            check("status menyebut masa berlaku QR",
                "QR berlaku sampai" in text, text)
            check("masih menunggu (belum lunas)", ns['order_data']['payment_in_progress'] is True)

            # order_id harus unik. Dulu formatnya hanya sampai detik, jadi dua
            # transaksi dalam detik yang sama ditolak API dengan 409. Sekarang
            # ada 4 digit acak di belakangnya — diperiksa dari catatan mesin,
            # karena order_id tidak disimpan sebagai variabel global.
            import re as _re
            try:
                with open(os.environ["VENDING_LOG"], encoding="utf-8") as file:
                    log_content = file.read()
            except OSError:
                log_content = ""
            match = _re.search(r"INV-\d{8}-\d{6}-[0-9a-f]{4}", log_content)
            check("order_id unik (ada akhiran acak)", match is not None,
                match.group(0) if match else log_content[:200])
            check("catatan mesin menyimpan tautan pembayaran",
                "link dibuat" in log_content, log_content[:200])

            # hentikan transaksi pertama supaya uji berikutnya bersih
            ns['cancel_payment']()
            root.update()
            check("batal transaksi live: sedang_bayar False", ns['order_data']['payment_in_progress'] is False)
            check("batal transaksi live: tombol bayar aktif",
                ns["ui"]['pay_button']["state"] == "normal", ns["ui"]['pay_button']["state"])
            check("batal transaksi live: panel QR kembali kosong",
                ns["ui"]['qr_label'].image is None
                and ns["ui"]["qr_state"]["placeholder"].winfo_manager() == "pack",
                f"image={ns['ui']['qr_label'].image} "
                f"placeholder={ns['ui']['qr_state']['placeholder'].winfo_manager()}")
        else:
            # mode simulasi: alur selesai sendiri setelah ~6 detik
            pump(root, 4 if mode == "demo-sandbox" else 9)
            if mode == "demo-sandbox":
                check("alur bayar sandbox dipanggil tanpa API sungguhan dalam tes",
                    len(sandbox_payment_calls) == 1, sandbox_payment_calls)
                check("pembayaran sandbox tidak memeriksa Arduino",
                    ns["dispenser_ready"] is False)
            check("transaksi selesai: pesanan kosong", ns['order_data']['items'] == [], ns['order_data']['items'])
            check("transaksi selesai: total 0", ns['order_data']['total_amount'] == 0, ns['order_data']['total_amount'])
            check("transaksi selesai: sedang_bayar False", ns['order_data']['payment_in_progress'] is False)
            check("transaksi selesai: tombol bayar mati lagi (keranjang kosong)",
                ns["ui"]['pay_button']["state"] == "disabled", ns["ui"]['pay_button']["state"])
            check("tombol batal disembunyikan", ns["ui"]['cancel_button'].winfo_manager() == "",
                ns["ui"]['cancel_button'].winfo_manager())
            check("transaksi selesai: panel QR kembali kosong",
                ns["ui"]['qr_label'].image is None
                and ns["ui"]["qr_state"]["placeholder"].winfo_manager() == "pack",
                f"image={ns['ui']['qr_label'].image} "
                f"placeholder={ns['ui']['qr_state']['placeholder'].winfo_manager()}")

            # Layar sukses menggantikan messagebox: mesin vending tidak
            # seharusnya meminta pelanggan menutup dialog.
            check("layar sukses tampil",
                ns["ui"]['success_screen']["frame"] is not None)
            if mode in ("demo", "demo-sandbox"):
                success_frame = ns["ui"]['success_screen']["frame"]
                success_labels = [
                    widget.cget("text")
                    for container in success_frame.winfo_children()
                    for widget in container.winfo_children()
                    if isinstance(widget, tkinter.Label)
                ]
                expected_success_message = (
                    "Uji sandbox; tidak ada produk fisik dikeluarkan."
                    if mode == "demo-sandbox"
                    else "Simulasi saja; tidak ada produk fisik dikeluarkan."
                )
                check("layar sukses mode demo menjelaskan pembayaran dan dispenser",
                    expected_success_message in success_labels
                    and (
                        mode != "demo-sandbox"
                        or "Pembayaran sandbox berhasil" in success_labels
                    ),
                    success_labels)
                with open(os.environ["VENDING_LOG"], encoding="utf-8") as file:
                    demo_log = file.read()
                expected_log = (
                    "pembayaran sandbox diterima"
                    if mode == "demo-sandbox"
                    else "tidak ada produk fisik dikeluarkan"
                )
                check("log mencatat mode demo tanpa mengklaim barang keluar",
                    expected_log in demo_log
                    and "tidak ada produk fisik dikeluarkan" in demo_log,
                    demo_log[-500:])
            check("sukses tidak memakai popup messagebox",
                not any("Transaksi Berhasil" in str(a) for _, a in recorded_calls), recorded_calls)
            ns["ui"]['close_success_screen']()
            root.update()
            check("layar sukses bisa ditutup",
                ns["ui"]['success_screen']["frame"] is None)

        # --- uji batal pada transaksi baru ---
        # nilai total berbeda antar mode (live masih menyimpan pesanan lama),
        # jadi periksa kenaikannya, bukan angka mutlaknya.
        before = ns['order_data']['total_amount']
        ns['select_product'](2)     # Teh Botol 4.000
        root.update()
        check("produk bisa ditambah lagi", ns['order_data']['total_amount'] == before + 4000,
            f"{before} -> {ns['order_data']['total_amount']}")
        ns['start_qris_payment']()
        root.update()
        check("transaksi kedua berjalan", ns['order_data']['payment_in_progress'] is True)
        check("batal: tombol batal muncul", ns["ui"]['cancel_button'].winfo_manager() == "pack",
            ns["ui"]['cancel_button'].winfo_manager())
        ns['cancel_payment']()
        root.update()
        check("batal: sedang_bayar False", ns['order_data']['payment_in_progress'] is False)
        check("batal: tombol bayar aktif", ns["ui"]['pay_button']["state"] == "normal",
            ns["ui"]['pay_button']["state"])
        # Kalau pembatalan terjadi selagi create_payment() masih berjalan, worker
        # bisa menimpanya kembali setelah batal_pembayaran() mengosongkannya.
        # Tautan basi yang tertinggal bikin keadaan jadi tidak konsisten:
        # sedang_bayar False tapi link_bayar terisi.
        check("batal: tidak ada tautan basi yang tertinggal",
            ns['order_data']['payment_link'] is None, ns['order_data']['payment_link'])
        check("batal: tombol batal hilang", ns["ui"]['cancel_button'].winfo_manager() == "",
            ns["ui"]['cancel_button'].winfo_manager())
        check("batal: pesanan tidak ikut terhapus", ns['order_data']['total_amount'] == before + 4000,
            ns['order_data']['total_amount'])

        # Uji alur SumoPod yang sekarang berada di main.py memakai klien tiruan:
        # tes ini tidak membuat transaksi sungguhan.
        payment_link = "https://example.test/payment-links/demo"
        payment_detail = {
            "payment_link_url": payment_link,
            "expires_at": "2026-10-09T00:00:00+07:00",
            "fee": 500,
            "net_amount": 9500,
        }
        payment_requests = []
        fake_client = SimpleNamespace(
            create_payment=lambda **kwargs: (
                payment_requests.append(kwargs) or payment_detail
            ),
            get_payment_link=lambda _link: {"status": "PAID"},
            is_paid=lambda _detail: True,
            payin_status=lambda _detail: "SUCCESS",
        )
        queued_callbacks = []
        saved_links = []
        status_updates = []
        summaries = []
        qr_images = []
        dispensed_products = []
        checkout_qr = qr_image_for_test
        ns["process_live_payment"](
            payment_client=fake_client,
            amount=10_000,
            cancel_event=threading.Event(),
            log_event_callback=lambda _message: None,
            post_to_ui=lambda function, *args, **kwargs: (
                queued_callbacks.append((function, args, kwargs))
            ),
            save_payment_link=saved_links.append,
            set_status=lambda *args: status_updates.append(args),
            show_payment_summary=summaries.append,
            dispense_product=lambda: dispensed_products.append(True),
            failure_callback=lambda _message: None,
            display_qr_image=lambda image, text: qr_images.append((image, text)),
            show_payment_link_qr=lambda _link: None,
        )
        for function, args, kwargs in queued_callbacks:
            function(*args, **kwargs)
        check(
            "main.py membuat pembayaran melalui klien SumoPod",
            len(payment_requests) == 1
            and payment_requests[0]["amount"] == 10_000
            and payment_requests[0]["expires_in_hours"] == 1,
            payment_requests,
        )
        check("tautan pembayaran tersimpan", saved_links == [payment_link], saved_links)
        check("ringkasan pembayaran ditampilkan", summaries == [payment_detail])
        check(
            "QR checkout ditampilkan",
            qr_images == [(checkout_qr, "Scan QRIS untuk membayar")],
            [description for _image, description in qr_images],
        )
        check("pembayaran lunas mengeluarkan produk", dispensed_products == [True])
        check(
            "status pembayaran berhasil ditampilkan",
            any(message == "Pembayaran berhasil!" for message, *_ in status_updates),
            status_updates,
        )

    tkinter.Tk.mainloop = fake_mainloop

    # messagebox menunggu klik user — ganti dengan pencatat
    from tkinter import messagebox
    recorded_calls = []
    messagebox.showinfo = lambda *a, **k: recorded_calls.append(("info", a))
    messagebox.showwarning = lambda *a, **k: recorded_calls.append(("warning", a))

    with open(SRC, encoding="utf-8") as f:
        code = f.read()

    ns["__name__"] = "__main__"
    ns["__file__"] = SRC
    original_qr_fetcher = qris_payment.fetch_checkout_qr
    qr_image_for_test = object()
    qris_payment.fetch_checkout_qr = lambda _client, _link: qr_image_for_test
    try:
        exec(compile(code, SRC, "exec"), ns)
    except SystemExit:
        pass
    except Exception:
        import traceback
        result['error'] = result['error'] or traceback.format_exc()
    finally:
        qris_payment.fetch_checkout_qr = original_qr_fetcher

    return result


def main():
    if "--child" in sys.argv:
        mode = sys.argv[sys.argv.index("--child") + 1]
        r = _run_child(mode)
        print(f"@@RESULT@@{mode}@@{r!r}")
        return 0

    modes = ["live"] if "--live" in sys.argv else [
        "simulation", "demo", "demo-sandbox",
    ]

    if "live" in modes and not _has_api_key():
        print("Lewati mode live: API key tidak ada di environment variable maupun .env.")
        modes.remove("live")

    failure_count = 0
    for mode in modes:
        print(f"\n{'=' * 60}\nMODE: {mode.upper()}\n{'=' * 60}")
        env = dict(os.environ)
        env["VENDING_SERIAL_PORT"] = ""
        env["SUMOPOD_SANDBOX"] = "1"
        if mode == "simulation":
            # Empty key and MODE_DEMO=0 force ordinary no-key simulation.
            env["SUMOPOD_API_KEY"] = ""
            env["MODE_DEMO"] = "0"
        elif mode == "demo":
            # Production selection remains disabled in demo, even with a key.
            env["SUMOPOD_API_KEY"] = "demo-test-key"
            env["MODE_DEMO"] = "1"
            env["SUMOPOD_SANDBOX"] = "0"
        elif mode == "demo-sandbox":
            # A dummy key creates only a sandbox client; test payment calls are stubbed.
            env["SUMOPOD_API_KEY"] = "demo-test-key"
            env["MODE_DEMO"] = "1"
        else:
            env["MODE_DEMO"] = "0"

        # Stok diarahkan ke berkas sementara supaya uji tidak mengubah stok
        # asli milik pengguna. Isinya sengaja {"Air Mineral": 5} — berbeda dari
        # nilai bawaan 15 — supaya pemuatan stok tersimpan benar-benar teruji.
        stock_file = os.path.join(tempfile.gettempdir(), f"vending_stock_test_{mode}.json")
        try:
            os.remove(stock_file)
        except OSError:
            pass
        with open(stock_file, "w", encoding="utf-8") as file:
            json.dump({"Air Mineral": 5}, file)
        env['VENDING_STOCK'] = stock_file

        # Catatan mesin juga diarahkan ke berkas sementara, supaya menjalankan
        # uji tidak menumpuk di catatan asli mesin.
        log_file = os.path.join(tempfile.gettempdir(), f"vending_log_test_{mode}.log")
        try:
            os.remove(log_file)
        except OSError:
            pass
        env["VENDING_LOG"] = log_file
        env["PYTHONIOENCODING"] = "utf-8"

        p = subprocess.run([sys.executable, __file__, "--child", mode],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env)
        result = None
        for line in p.stdout.splitlines():
            if line.startswith("@@RESULT@@"):
                remainder = line.split("@@RESULT@@", 1)[1]
                _, _, payload = remainder.partition("@@")
                result = eval(payload)          # noqa: S307 - keluaran proses sendiri

        if result is None:
            print("Proses anak gagal dijalankan.")
            print(p.stdout[-1500:])
            print(p.stderr[-1500:])
            failure_count += 1
            continue

        if result['error']:
            print("EXCEPTION:")
            print(result['error'])
            failure_count += 1

        for name, ok, info in result['checks']:
            print(f"  [{'OK' if ok else 'GAGAL'}] {name}" + ("" if ok else f"  -> {info}"))
            if not ok:
                failure_count += 1

        for line in result["info"]:
            print(f"  info: {line}")

    print(f"\n{'=' * 60}")
    print("SEMUA LULUS" if failure_count == 0 else f"TOTAL GAGAL: {failure_count}")
    print("=" * 60)
    return 1 if failure_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
