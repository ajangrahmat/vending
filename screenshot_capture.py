"""
screenshot_capture.py — Ambil tangkapan layar jendela vending machine + ukur
apakah halaman masih perlu digulir.

Dipisahkan dari test_main_gui.py karena tujuannya berbeda:

  test_main_gui.py   -> memeriksa PERILAKU (apakah tombol, stok, QR benar)
  screenshot_capture.py -> memeriksa TAMPILAN (apakah muat di layar, bagaimana
                        hasilnya terlihat)

Angka "muat / SKROLL" dihitung dari tinggi yang diminta halaman
(page.winfo_reqheight()) dibanding tinggi kanvas yang tersedia
(canvas.winfo_height()). Kalau konten lebih tinggi dari kanvas, pengguna
layar sentuh harus menggeser — dan itu yang ingin dihindari.

Pakai:
    py screenshot_capture.py                 # mode simulasi, 3 tangkapan
    SUMOPOD_API_KEY=xxx py screenshot_capture.py --live
"""

from __future__ import annotations

import os
import sys
import time
import tkinter

from PIL import ImageGrab

SRC = "main.py"


def _get_prefix(size):
    """Awalan nama berkas potret. Membedakan hasil antar-ukuran layar supaya
    potret 1366x768 tidak menimpa potret 1080p."""
    if not size:
        return "screen_1080p"
    return "screen_" + size.split("+")[0]


def _run_child(mode, size=None):
    """Proses anak: exec main.py dengan mainloop dipatch, lalu tangkap layar."""
    ns = {}
    fit_job_id = _get_prefix(size)
    result = {'measurements': [], 'error': None, 'files': [], "qr": None, 'capture_failures': [],
             'size': size, 'prefix': fit_job_id}

    def pump(root, seconds):
        end_time = time.monotonic() + seconds
        while time.monotonic() < end_time:
            root.update()
            time.sleep(0.02)

    def wait_for_layout(root, deadline=6.0):
        """Proses event sampai tata letak mengendap DAN konsisten.

        Tata letak di sini bertingkat: jendela dimaksimalkan -> kanvas berubah
        -> halaman dipaksa setinggi kanvas -> kartu meregang -> gambar
        diskalakan ulang (ditunda 120 ms).

        Menunggu "ukuran berhenti berubah" saja TIDAK cukup, dan itu pernah
        membuat saya salah lapor: ukurannya berhenti di nilai yang SALAH (tinggi
        halaman terpatok terlalu pendek), jadi terlihat "diam" lalu dinyatakan
        muat, padahal isinya terpotong. Karena itu syaratnya ditambah: tinggi
        halaman harus benar-benar sama dengan max(kebutuhan, tinggi kanvas).
        """
        end_time = time.monotonic() + deadline
        previous = None
        stable_checks = 0
        while time.monotonic() < end_time:
            root.update()
            time.sleep(0.05)
            canvas = ns['canvas']
            page = ns['page']
            current = (page.winfo_height(), ns['product_cards'][0].winfo_height(),
                        ns['left_panel'].winfo_height(), ns['right_panel'].winfo_height())
            # Konsisten = tinggi halaman memang mengikuti isinya.
            is_consistent = page.winfo_height() >= max(page.winfo_reqheight(),
                                                      canvas.winfo_height())
            if current == previous and is_consistent:
                stable_checks += 1
                if stable_checks >= 6:
                    return
            else:
                stable_checks = 0
            previous = current

    def measure_layout(root, title):
        """Catat apakah seluruh halaman terlihat, dan kembalikan statusnya.

        Patokannya canvas.yview(), bukan perbandingan tinggi. yview() adalah
        jawaban langsung dari Tk atas pertanyaan "berapa bagian halaman yang
        terlihat?" — nilainya 1.0 berarti seluruhnya terlihat, kurang dari itu
        berarti pelanggan harus menggeser. Membandingkan angka tinggi pernah
        menyesatkan: tinggi halaman bisa tersangkut di nilai lama sehingga
        terlihat "muat" padahal bilah gulirnya masih aktif.
        """
        canvas = ns['canvas']
        root.update_idletasks()
        root.update()
        y0, y1 = canvas.yview()
        page = ns['page']
        required_height = page.winfo_reqheight()
        height = canvas.winfo_height()
        # Dua cara gagal, dan keduanya harus ketahuan:
        #   SKROLL     -> halaman lebih tinggi dari kanvas, jadi perlu digulir
        #   TERPOTONG  -> tinggi halaman kurang dari kebutuhan isinya, jadi
        #                 bagian bawah hilang dan TIDAK BISA digulir sama sekali
        #                 (ini yang paling berbahaya: tombol BAYAR bisa hilang)
        if page.winfo_height() < max(required_height, height):
            status = "TERPOTONG"
        elif y1 >= 0.999:
            status = "muat"
        else:
            status = "SKROLL"
        result['measurements'].append(
            (title, required_height, height, y1, status,
             ns['right_panel'].winfo_height(), ns['left_panel'].winfo_height()))
        return status

    def capture_screenshot(root, name):
        """Simpan isi jendela apa adanya (bukan layar penuh)."""
        root.update_idletasks()
        root.update()
        # ImageGrab menyalin APA ADANYA dari layar, jadi jendela harus benar-
        # benar di depan. Tanpa topmost, jendela lain yang menutupi akan ikut
        # tertangkap dan hasilnya menyesatkan.
        root.attributes("-topmost", True)
        root.lift()
        root.update()
        time.sleep(0.35)            # beri waktu Windows menggambar ulang
        root.update()
        x, y = root.winfo_rootx(), root.winfo_rooty()
        w, h = root.winfo_width(), root.winfo_height()
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            f"{fit_job_id}_{name}.png")
        # ImageGrab sesekali gagal ("screen grab failed") — misalnya saat
        # desktop sedang sibuk atau layar terkunci sebentar. Itu gangguan
        # sesaat, bukan alasan menggagalkan seluruh pengukuran tata letak.
        for attempts in range(4):
            try:
                image = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                break
            except OSError:
                if attempts == 3:
                    # Kegagalan menangkap layar TIDAK boleh membatalkan
                    # pengukuran tata letak — itu bagian yang paling penting.
                    result['capture_failures'].append(name)
                    return None
                time.sleep(0.8)
                root.update()
        image.save(path)
        root.attributes("-topmost", False)
        result['files'].append((name, path, w, h))
        return path

    def scenario(root):
        # Kalau diminta ukuran tertentu, jangan pakai jendela penuh: kembalikan
        # ke keadaan normal dulu, karena jendela yang di-zoom mengabaikan
        # geometry() dan semua ukuran akan melaporkan angka yang sama.
        if size:
            root.state("normal")
            root.geometry(size + "+0+0")
            for _ in range(30):
                root.update()
                time.sleep(0.02)

        root.update()
        wait_for_layout(root)

        measure_layout(root, "empty cart")
        capture_screenshot(root, "1_empty")

        # Keranjang penuh: seluruh 6 jenis produk — inilah beban terberat,
        # karena panel pesanan memanjang dan itu yang dulu bikin menggulir.
        for i in range(len(ns['products'])):
            ns['select_product'](i)
            root.update()
        wait_for_layout(root)

        measure_layout(root, "full cart")
        capture_screenshot(root, "2_full_cart")

        if mode == "live":
            ns['start_qris_payment']()
            deadline = time.monotonic() + 45
            while ns['order_data']['payment_link'] is None and time.monotonic() < deadline:
                root.update()
                time.sleep(0.05)
            # Tunggu sampai teks label BERUBAH dari kalimat awal. Sebelumnya di
            # sini dipakai "== 'Scan QRIS untuk membayar'", padahal teks awalnya
            # "Tekan tombol bayar..." — jadi syaratnya langsung salah dan QR
            # belum sempat terpasang saat tangkapan diambil.
            deadline = time.monotonic() + 30
            while (ns['scan_label']["text"] == "Tekan tombol bayar untuk menampilkan QRIS"
                   and time.monotonic() < deadline):
                root.update()
                time.sleep(0.05)
            wait_for_layout(root)
            # Catat keadaan QR-nya. Tanpa ini, tangkapan layar yang isinya masih
            # placeholder bisa lolos tanpa ketahuan — persis yang sempat terjadi.
            result["qr"] = (ns['qr_label'].image is not None,
                           ns['scan_label']["text"])
            measure_layout(root, "QR displayed")
            capture_screenshot(root, "3_payment")
            ns['cancel_payment']()
            root.update()
        else:
            ns['start_qris_payment']()
            pump(root, 0.8)
            measure_layout(root, "payment pending")
            capture_screenshot(root, "3_payment")
            pump(root, 9)
            if ns['ui']['success_screen']['frame'] is not None:
                root.update()
                time.sleep(0.3)
                capture_screenshot(root, "4_success")
                ns['ui']['close_success_screen']()
                root.update()

    original_mainloop = tkinter.Tk.mainloop

    def fake_mainloop(self):
        try:
            scenario(self)
        except Exception:
            import traceback
            result['error'] = traceback.format_exc()
        finally:
            try:
                self.destroy()
            except Exception:
                pass

    tkinter.Tk.mainloop = fake_mainloop

    with open(SRC, encoding="utf-8") as file:
        code = file.read()

    ns["__name__"] = "__main__"
    ns["__file__"] = SRC
    try:
        exec(compile(code, SRC, "exec"), ns)
    except SystemExit:
        pass
    except Exception:
        import traceback
        result['error'] = result['error'] or traceback.format_exc()

    return result


def main():
    if "--child" in sys.argv:
        mode = sys.argv[sys.argv.index("--child") + 1]
        size = None
        if '--size' in sys.argv:
            size = sys.argv[sys.argv.index('--size') + 1]
        r = _run_child(mode, size)
        print(f"@@RESULT@@{r!r}")
        return 0

    mode = "live" if "--live" in sys.argv else "simulation"
    # --size 1366x768 : paksa ukuran jendela tertentu, untuk memeriksa apakah
    # aplikasi muat di layar selain 1080p (mis. panel sentuh yang lebih kecil).
    size = None
    if '--size' in sys.argv:
        size = sys.argv[sys.argv.index('--size') + 1]
    env = dict(os.environ)
    if mode == "simulation":
        env["SUMOPOD_API_KEY"] = ""
    # Stok diarahkan ke berkas sementara supaya tangkapan layar tidak
    # mengurangi stok asli milik pengguna.
    import json
    import tempfile
    stock_file = os.path.join(tempfile.gettempdir(), "vending_screenshot_stock.json")
    with open(stock_file, "w", encoding="utf-8") as file:
        json.dump({}, file)
    env['VENDING_STOCK'] = stock_file
    # Catatan mesin juga diarahkan ke berkas sementara.
    env["VENDING_LOG"] = os.path.join(tempfile.gettempdir(), "vending_screenshot.log")

    import subprocess
    command = [sys.executable, __file__, "--child", mode]
    if size:
        command += ['--size', size]
    p = subprocess.run(command, capture_output=True, text=True, env=env)

    result = None
    for line in p.stdout.splitlines():
        if line.startswith("@@RESULT@@"):
            result = eval(line.split("@@RESULT@@", 1)[1])   # noqa: S307

    if result is None:
        print("Proses anak gagal:")
        print(p.stdout[-2000:])
        print(p.stderr[-2000:])
        return 1

    if result['error']:
        print("EXCEPTION:\n" + result['error'])
        return 1

    print(f"MODE: {mode.upper()}"
          + (f"   UKURAN DIPAKSA: {size}" if size else "   (jendela penuh)")
          + "\n")
    print(f"{'kondisi':<22} {'butuh':>7} {'kanvas':>7} {'yview':>7}   status")
    print("-" * 66)
    failure_callback = 0
    for title, required_height, canvas, y1, status, panel, left_panel in result['measurements']:
        marker = "" if status == "muat" else "   <-- HARUS DIGULIR"
        print(f"{title:<22} {required_height:>7} {canvas:>7} {y1:>7.3f}   {status}{marker}")
        print(f"{'(panel %d, kolom produk diregangkan ke %d)' % (panel, left_panel):>66}")
        if status != "muat":
            failure_callback += 1

    print("\nTangkapan layar:")
    for name, path, w, h in result['files']:
        print(f"  {name:<18} {w}x{h}  {os.path.basename(path)}")

    if result['capture_failures']:
        # Sengaja TIDAK dihitung sebagai kegagalan: kode keluar skrip ini
        # menandakan "ada kondisi yang masih perlu digulir". Kegagalan memotret
        # layar (sesi desktop terkunci / remote terputus) adalah gangguan
        # lingkungan, bukan kemunduran tata letak — kalau dicampur, kode
        # keluarnya jadi tidak bisa dipercaya.
        print(f"\nPERINGATAN: gagal menangkap layar: {', '.join(result['capture_failures'])}"
              "\n  (pengukuran tata letak di atas tetap sahih;"
              " tangkapan lama di folder ini belum diperbarui)")

    if result["qr"] is not None:
        has_qr, text = result["qr"]
        print(f"\nQR asli terpasang: {'ya' if has_qr else 'TIDAK'}")
        print(f"  teks label: {text!r}")
        if not has_qr:
            failure_callback += 1

    print()
    if failure_callback:
        print(f"SELESAI — {failure_callback} kondisi masih perlu digulir")
    else:
        print("SELESAI — semua kondisi muat tanpa menggulir")
    return 1 if failure_callback else 0


if __name__ == "__main__":
    raise SystemExit(main())
