"""Pembuatan tampilan Tkinter.

Ubah susunan, ukuran, dan teks tampilan di file ini. Aksi tombol disediakan
oleh main.py, jadi aturan belanja dan pembayaran tetap berada di sana.
"""

import os
import tkinter as tk
from tkinter import font as tkfont

from PIL import Image, ImageTk

from cart import summarize_cart as summarize_order
from inventory import resolve_asset_path

try:
    import qrcode
except ImportError:
    qrcode = None

from theme import (
    BG_COLOR,
    BORDER_COLOR,
    CARD_BG,
    DANGER_COLOR,
    DISABLED_COLOR,
    PRIMARY_COLOR,
    PRIMARY_HOVER,
    PRIMARY_LIGHT,
    SUCCESS_COLOR,
    SUCCESS_HOVER,
    SUCCESS_LIGHT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


BREAKPOINT_WIDE = 1000
PANEL_WIDTH = 380
CARD_MIN_WIDTH = 230
PAD = 24
QR_SIZE = 212


def create_ui(root, products, actions, format_currency, live_mode,
              demo_mode=False):
    """Buat seluruh widget dan kembalikan referensinya untuk main.py."""
    available_font_families = set(tkfont.families())
    primary_font = next(
        (name for name in (
            "Segoe UI", "SF Pro Text", "Helvetica Neue", "Noto Sans",
            "DejaVu Sans", "Arial",
        ) if name in available_font_families),
        "Arial",
    )

    def font(size, bold=False):
        return (primary_font, size, "bold" if bold else "normal")

    def attach_hover(button, normal, hover):
        button.bind("<Enter>", lambda _e: button["state"] == "normal"
                    and button.config(bg=hover))
        button.bind("<Leave>", lambda _e: button["state"] == "normal"
                    and button.config(bg=normal))

    ui = {}

    header = tk.Frame(root, bg=PRIMARY_COLOR)
    header.pack(fill="x")
    header_inner = tk.Frame(header, bg=PRIMARY_COLOR)
    header_inner.pack(fill="x", padx=PAD, pady=14)

    logo = tk.Canvas(header_inner, width=44, height=44, bg=PRIMARY_COLOR,
                     highlightthickness=0)
    logo.pack(side="left", padx=(0, 14))
    logo.create_rectangle(10, 4, 36, 40, fill="#0D47A1",
                          outline="#64B5F6", width=2)
    logo.create_rectangle(14, 8, 32, 20, fill="#BBDEFB",
                          outline="#90CAF9", width=1)
    logo.create_rectangle(16, 23, 30, 29, fill="#FFF3E0",
                          outline="#FFB74D", width=1)
    logo.create_oval(20, 33, 26, 38, fill="#FFF3E0",
                     outline="#FFB74D", width=1)

    brand = tk.Frame(header_inner, bg=PRIMARY_COLOR)
    brand.pack(side="left")
    tk.Label(brand, text="Mini Vending Machine", font=font(16, True),
             bg=PRIMARY_COLOR, fg="white").pack(anchor="w")
    tagline_label = tk.Label(brand, text="Praktis  •  Cepat  •  Aman",
                             font=font(9), bg=PRIMARY_COLOR, fg="#BBDEFB")
    tagline_label.pack(anchor="w")
    clock_label = tk.Label(header_inner, text="", font=font(11, True),
                           bg=PRIMARY_COLOR, fg="white")
    clock_label.pack(side="right")

    body = tk.Frame(root, bg=BG_COLOR)
    body.pack(fill="both", expand=True)
    scrollbar = tk.Scrollbar(body, orient="vertical")
    scrollbar.pack(side="right", fill="y")
    canvas = tk.Canvas(body, bg=BG_COLOR, highlightthickness=0,
                       yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=canvas.yview)
    page = tk.Frame(canvas, bg=BG_COLOR)
    page_window = canvas.create_window((0, 0), window=page, anchor="nw")

    left_panel = tk.Frame(page, bg=BG_COLOR)
    right_panel = tk.Frame(page, bg=CARD_BG, highlightbackground=BORDER_COLOR,
                     highlightthickness=1)
    tk.Label(left_panel, text="Pilih Produk", font=font(20, True), bg=BG_COLOR,
             fg=TEXT_PRIMARY).pack(anchor="w")
    tk.Label(left_panel, text="Pilih minuman atau camilan favoritmu", font=font(10),
             bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(2, 20))
    grid_container = tk.Frame(left_panel, bg=BG_COLOR)
    grid_container.pack(fill="both", expand=True)

    stock_labels = []
    buy_buttons = []
    product_cards = []
    image_references = []
    product_image_labels = []

    for index, item in enumerate(products):
        card = tk.Frame(grid_container, bg=CARD_BG,
                        highlightbackground=BORDER_COLOR, highlightthickness=1)
        product_cards.append(card)

        img_frame = tk.Frame(card, bg=PRIMARY_LIGHT, height=130)
        img_frame.pack(fill="x")
        img_frame.pack_propagate(False)
        image_path = resolve_asset_path(item['image'])
        if image_path and os.path.exists(image_path):
            resized_image = Image.open(image_path)
            resized_image.thumbnail((110, 110), Image.Resampling.LANCZOS)
            photo_image = ImageTk.PhotoImage(resized_image)
            image_references.append(photo_image)
            image_label = tk.Label(img_frame, image=photo_image, bg=PRIMARY_LIGHT)
        else:
            image_label = tk.Label(
                img_frame, text=item['name'][0], font=font(34, True),
                bg=PRIMARY_LIGHT, fg=PRIMARY_COLOR,
            )
        image_label.pack(expand=True)
        product_image_labels.append(image_label)

        content = tk.Frame(card, bg=CARD_BG)
        content.pack(fill="both", expand=True, padx=20, pady=18)
        tk.Label(content, text=item['name'], font=font(14, True), bg=CARD_BG,
                 fg=TEXT_PRIMARY, anchor="w").pack(fill="x")
        tk.Label(content, text=format_currency(item['price']), font=font(14, True),
                 bg=CARD_BG, fg=PRIMARY_COLOR, anchor="w").pack(fill="x", pady=(4, 0))

        stock_row = tk.Frame(content, bg=CARD_BG)
        stock_row.pack(fill="x", pady=(12, 0))
        stock = tk.Label(stock_row, text=f"Stok: {item['stock']}",
                         font=font(9, True), bg=SUCCESS_LIGHT,
                         fg=SUCCESS_COLOR, padx=10, pady=4)
        stock.pack(side="left")
        stock_labels.append(stock)

        buy = tk.Button(
            content, text="Beli", font=font(11, True), bg=PRIMARY_COLOR,
            fg="white", activebackground=PRIMARY_HOVER,
            activeforeground="white", relief="flat", bd=0, cursor="hand2",
            command=lambda i=index: actions['select_product'](i),
        )
        buy.pack(fill="x", pady=(18, 0), ipady=9)
        attach_hover(buy, PRIMARY_COLOR, PRIMARY_HOVER)
        buy_buttons.append(buy)

    panel = tk.Frame(right_panel, bg=CARD_BG)
    panel.pack(fill="both", expand=True, padx=24, pady=24)
    tk.Label(panel, text="Detail Pesanan", font=font(16, True), bg=CARD_BG,
             fg=TEXT_PRIMARY).pack(anchor="w")
    order_details_frame = tk.Frame(panel, bg=CARD_BG)
    order_details_frame.pack(fill="x", pady=(12, 0))
    tk.Frame(panel, height=1, bg=BORDER_COLOR).pack(fill="x", pady=18)

    total_row = tk.Frame(panel, bg=CARD_BG)
    total_row.pack(fill="x")
    tk.Label(total_row, text="Total", font=font(13, True), bg=CARD_BG,
             fg=TEXT_PRIMARY).pack(side="left")
    total_label = tk.Label(total_row, text="Rp 0", font=font(20, True),
                           bg=CARD_BG, fg=PRIMARY_COLOR)
    total_label.pack(side="right")

    notification_label = tk.Label(panel, text=" ", font=font(9), bg=CARD_BG,
                           fg=SUCCESS_COLOR, anchor="e")
    notification_label.pack(fill="x")

    qr_state = {"placeholder": None}
    tk.Label(panel, text="Pembayaran QRIS", font=font(14, True), bg=CARD_BG,
             fg=TEXT_PRIMARY).pack(anchor="w", pady=(28, 12))
    qris_box = tk.Frame(panel, bg=PRIMARY_LIGHT,
                        highlightbackground=BORDER_COLOR, highlightthickness=1)
    qris_box.pack(fill="x")
    qr_holder = tk.Frame(qris_box, bg="white", width=QR_SIZE, height=QR_SIZE)
    qr_holder.pack(pady=(18, 10))
    qr_holder.pack_propagate(False)
    qr_label = tk.Label(qr_holder, bg="white")
    scan_label = tk.Label(
        qris_box, text="Tekan tombol bayar untuk menampilkan QRIS",
        font=font(9), bg=PRIMARY_LIGHT, fg=TEXT_MUTED,
        wraplength=280, justify="center",
    )
    scan_label.pack(pady=(0, 16), padx=12)

    def create_qr_placeholder():
        placeholder = tk.Canvas(qr_holder, width=QR_SIZE, height=QR_SIZE,
                                bg="white", highlightthickness=0)
        placeholder.pack()
        placeholder.create_rectangle(4, 4, 207, 207, outline=BORDER_COLOR,
                                     dash=(6, 5), width=2)
        placeholder.create_text(106, 96, text="QRIS", font=font(16, True),
                                fill=TEXT_MUTED)
        placeholder.create_text(106, 122, text="muncul di sini",
                                font=font(9), fill=TEXT_MUTED)
        return placeholder

    def show_qr(image, description):
        placeholder = qr_state["placeholder"]
        if image is not None:
            if placeholder is not None:
                placeholder.pack_forget()
            if qr_label.winfo_manager() == "":
                qr_label.pack(expand=True)
            qr_label.config(image=image)
            qr_label.image = image
        else:
            if qr_label.winfo_manager() != "":
                qr_label.pack_forget()
            qr_label.config(image="")
            qr_label.image = None
            if placeholder is None:
                qr_state["placeholder"] = create_qr_placeholder()
            else:
                placeholder.pack()
        scan_label.config(text=description)

    def show_empty_qr():
        show_qr(None, "Tekan tombol bayar untuk menampilkan QRIS")

    def display_qr_image(resized_image, description):
        if resized_image is not None:
            show_qr(ImageTk.PhotoImage(resized_image), description)

    def show_payment_link_qr(link):
        if qrcode is None:
            show_qr(None, f"Buka halaman ini untuk membayar:\n{link}")
            return
        image = qrcode.make(link)
        image.thumbnail((210, 210), Image.Resampling.NEAREST)
        show_qr(ImageTk.PhotoImage(image),
                     "Scan untuk membuka halaman pembayaran")

    show_empty_qr()

    pay_button = tk.Button(
        panel,
        text=(
            "BAYAR QRIS (SANDBOX)" if demo_mode and live_mode
            else "BAYAR (SIMULASI DEMO)" if demo_mode
            else "BAYAR DENGAN QRIS"
        ),
        font=font(11, True),
        bg=SUCCESS_COLOR, fg="white", activebackground=SUCCESS_HOVER,
        activeforeground="white", relief="flat", bd=0, cursor="hand2",
        command=actions['start_qris_payment'],
    )
    pay_button.pack(fill="x", pady=(20, 14), ipady=11)
    attach_hover(pay_button, SUCCESS_COLOR, SUCCESS_HOVER)
    cancel_button = tk.Button(
        panel, text="Batalkan pembayaran", font=font(10, True),
        bg=CARD_BG, fg=DANGER_COLOR, activebackground="#FFEBEE",
        activeforeground=DANGER_COLOR, relief="flat", bd=0, cursor="hand2",
        highlightbackground=BORDER_COLOR, highlightthickness=1,
        command=actions['cancel_payment'],
    )
    payment_status_label = tk.Label(
        panel, text="Menunggu pembayaran...", font=font(10),
        bg=PRIMARY_LIGHT, fg=TEXT_MUTED, pady=12,
    )
    payment_status_label.pack(fill="x")

    tk.Label(panel, text="Status Sistem", font=font(12, True), bg=CARD_BG,
             fg=TEXT_PRIMARY).pack(anchor="w", pady=(28, 10))
    status_rows = [
        ("Pembayaran",
         "MODE DEMO · SumoPod Sandbox" if demo_mode and live_mode else
         "MODE DEMO (simulasi)" if demo_mode else (
             "SumoPod live" if live_mode else "Mode simulasi"
         ),
         SUCCESS_COLOR if live_mode and not demo_mode else "#EF6C00"),
        ("Arduino / Dispenser",
         "Tidak diperlukan (mode demo)" if demo_mode else "Belum tersambung",
         TEXT_MUTED),
        ("Stok Produk", "Tersedia", SUCCESS_COLOR),
    ]
    system_status_labels = {}
    system_status_dots = {}
    for name, text, color in status_rows:
        row = tk.Frame(panel, bg=CARD_BG)
        row.pack(fill="x", pady=5)
        dot = tk.Canvas(row, width=10, height=10, bg=CARD_BG,
                        highlightthickness=0)
        dot.create_oval(1, 1, 9, 9, fill=color, outline="")
        dot.pack(side="left", padx=(0, 10))
        system_status_dots[name] = dot
        tk.Label(row, text=name, font=font(10), bg=CARD_BG,
                 fg=TEXT_SECONDARY).pack(side="left")
        value = tk.Label(row, text=text, font=font(10, True),
                         bg=CARD_BG, fg=color)
        value.pack(side="right")
        system_status_labels[name] = value

    btn_reset = tk.Button(
        panel, text="Kembalikan stok ke nilai awal", font=font(9),
        bg=CARD_BG, fg=TEXT_MUTED, activebackground=CARD_BG,
        activeforeground=PRIMARY_COLOR, relief="flat", bd=0, cursor="hand2",
        command=actions['reset_stock'],
    )
    btn_reset.pack(anchor="e", pady=(8, 0))

    def update_products(products, order_locked=False):
        for index, item in enumerate(products):
            is_out_of_stock = item['stock'] <= 0
            stock_labels[index].config(
                text="Habis" if is_out_of_stock else f"Stok: {item['stock']}",
                bg="#EEEEEE" if is_out_of_stock else SUCCESS_LIGHT,
                fg=TEXT_MUTED if is_out_of_stock else SUCCESS_COLOR,
            )
            if is_out_of_stock or order_locked:
                buy_buttons[index].config(
                    text="Stok Habis" if is_out_of_stock else "Beli",
                    state="disabled",
                    bg=DISABLED_COLOR, activebackground=DISABLED_COLOR,
                )
            else:
                buy_buttons[index].config(
                    text="Beli", state="normal",
                    bg=PRIMARY_COLOR, activebackground=PRIMARY_HOVER,
                )

        stock_status_label = system_status_labels.get("Stok Produk")
        if stock_status_label is not None:
            out_of_stock_count = sum(1 for item in products if item['stock'] <= 0)
            if out_of_stock_count == 0:
                stock_status_label.config(text="Tersedia", fg=SUCCESS_COLOR)
            elif out_of_stock_count == len(products):
                stock_status_label.config(text="Semua habis", fg=DANGER_COLOR)
            else:
                stock_status_label.config(text=f"{out_of_stock_count} produk habis",
                                   fg="#EF6C00")

    def update_system_status(name, text, color):
        status_label = system_status_labels.get(name)
        status_dot = system_status_dots.get(name)
        if status_label is None or status_dot is None:
            raise KeyError(f"Status sistem tidak ditemukan: {name}")
        status_label.config(text=text, fg=color)
        status_dot.itemconfig(1, fill=color)

    def update_order(
        order_items,
        total,
        payment_in_progress,
        remove_order_item,
        clear_order,
        format_currency,
        payment_ready=True,
    ):
        for widget in order_details_frame.winfo_children():
            widget.destroy()

        if not order_items:
            tk.Label(
                order_details_frame, text="Belum ada produk dipilih",
                font=font(11), fg=TEXT_MUTED, bg=CARD_BG,
            ).pack(anchor="w", pady=16)
        else:
            for name, qty, unit_price in summarize_order(order_items, products):
                row = tk.Frame(order_details_frame, bg=CARD_BG)
                row.pack(fill="x", pady=7)
                row.grid_columnconfigure(0, weight=1)
                tk.Label(
                    row, text=f"{qty}×  {name}", font=font(11, True),
                    bg=CARD_BG, fg=TEXT_PRIMARY, anchor="w",
                ).grid(row=0, column=0, sticky="w")
                tk.Label(
                    row, text=format_currency(unit_price * qty), font=font(11),
                    bg=CARD_BG, fg=TEXT_SECONDARY,
                ).grid(row=0, column=1, sticky="e", padx=(12, 8))

                remove = tk.Button(
                    row, text="\u2212", font=font(11, True), bg=CARD_BG,
                    fg=DANGER_COLOR, activebackground="#FFEBEE",
                    activeforeground=DANGER_COLOR, relief="flat", bd=0,
                    cursor="hand2", width=2,
                    command=lambda item_name=name: remove_order_item(item_name),
                )
                remove.grid(row=0, column=2, sticky="e")
                attach_hover(remove, CARD_BG, "#FFEBEE")

            clear = tk.Button(
                order_details_frame, text="Kosongkan pesanan", font=font(9, True),
                bg=CARD_BG, fg=TEXT_MUTED, activebackground=CARD_BG,
                activeforeground=DANGER_COLOR, relief="flat", bd=0,
                cursor="hand2", command=clear_order,
            )
            clear.pack(anchor="e", pady=(8, 0))
            attach_hover(clear, CARD_BG, CARD_BG)

        total_label.config(text=format_currency(total))
        if payment_in_progress or total <= 0 or not payment_ready:
            pay_button.config(state="disabled", bg=DISABLED_COLOR)
        else:
            pay_button.config(state="normal", bg=SUCCESS_COLOR)

    success_screen = {"frame": None}

    def close_success_screen():
        if success_screen["frame"] is not None:
            success_screen["frame"].destroy()
            success_screen["frame"] = None

    def show_success_screen():
        if success_screen["frame"] is not None:
            return

        overlay = tk.Frame(root, bg=SUCCESS_COLOR)
        success_screen["frame"] = overlay
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        overlay.lift()
        content = tk.Frame(overlay, bg=SUCCESS_COLOR)
        content.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(content, text="\u2713", font=font(88, True),
                 bg=SUCCESS_COLOR, fg="white").pack()
        success_title = (
            "Pembayaran sandbox berhasil" if demo_mode and live_mode
            else "Mode demo selesai" if demo_mode
            else "Pembayaran berhasil" if live_mode
            else "Simulasi selesai"
        )
        success_message = (
            "Uji sandbox; tidak ada produk fisik dikeluarkan."
            if demo_mode and live_mode else
            "Simulasi saja; tidak ada produk fisik dikeluarkan."
            if not live_mode else "Silakan ambil produk Anda"
        )
        tk.Label(content, text=success_title, font=font(24, True),
                 bg=SUCCESS_COLOR, fg="white").pack(pady=(6, 4))
        tk.Label(content, text=success_message, font=font(15),
                 bg=SUCCESS_COLOR, fg="#C8E6C9").pack()

        for widget in [overlay, content] + list(content.winfo_children()):
            widget.bind("<Button-1>", lambda _event: close_success_screen())
        root.after(6000, close_success_screen)

    state = {"mode": None, "cols": None}

    def arrange_grid(cols):
        for column in range(8):
            grid_container.grid_columnconfigure(column, weight=0, uniform="")
        for column in range(cols):
            grid_container.grid_columnconfigure(column, weight=1, uniform='product_cards')
        for index, card in enumerate(product_cards):
            row, column = divmod(index, cols)
            card.grid(
                row=row, column=column, sticky="nsew",
                padx=(0 if column == 0 else 10,
                      0 if column == cols - 1 else 10),
                pady=(0, 20),
            )

    def configure_layout(width):
        is_wide = width >= BREAKPOINT_WIDE
        pad = PAD if width >= 600 else 14
        if is_wide:
            available = width - PANEL_WIDTH - pad * 3
        else:
            available = width - pad * 2
        columns = max(1, min(4, available // CARD_MIN_WIDTH))
        mode = (is_wide, pad)
        if mode != state["mode"]:
            state["mode"] = mode
            left_panel.grid_forget()
            right_panel.grid_forget()
            for column in range(2):
                page.grid_columnconfigure(column, weight=0, minsize=0)
            page.grid_rowconfigure(0, weight=0)
            if is_wide:
                page.grid_columnconfigure(0, weight=1)
                page.grid_columnconfigure(1, weight=0, minsize=PANEL_WIDTH)
                page.grid_rowconfigure(0, weight=1)
                left_panel.grid(row=0, column=0, sticky="nsew",
                          padx=(pad, pad // 2), pady=pad)
                right_panel.grid(row=0, column=1, sticky="nsew",
                           padx=(pad // 2, pad), pady=pad)
            else:
                page.grid_columnconfigure(0, weight=1)
                left_panel.grid(row=0, column=0, sticky="nsew",
                          padx=pad, pady=(pad, 0))
                right_panel.grid(row=1, column=0, sticky="nsew",
                           padx=pad, pady=pad)
        if columns != state["cols"]:
            state["cols"] = columns
            arrange_grid(columns)
        if width < 520:
            tagline_label.pack_forget()
        elif not tagline_label.winfo_ismapped():
            tagline_label.pack(anchor="w")
        panel_width = PANEL_WIDTH if is_wide else width - pad * 2
        scan_label.config(wraplength=max(160, panel_width - 100))

    fit_to_size = None

    def fit_page_height():
        nonlocal fit_to_size
        fit_to_size = None
        required_height = page.winfo_reqheight()
        height = max(required_height, canvas.winfo_height())
        if canvas.itemcget(page_window, "height") != str(height):
            canvas.itemconfig(page_window, height=height)

    def schedule_fit(delay=30):
        nonlocal fit_to_size
        if fit_to_size is not None:
            root.after_cancel(fit_to_size)
        fit_to_size = root.after(delay, fit_page_height)

    def monitor_page_height():
        fit_page_height()
        root.after(150, monitor_page_height)

    def on_canvas_resize(event):
        canvas.itemconfig(page_window, width=event.width)
        configure_layout(event.width)
        schedule_fit()

    def on_page_resize(_event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        schedule_fit()
        if page.winfo_reqheight() <= canvas.winfo_height():
            canvas.yview_moveto(0)

    def scroll_page(event):
        if page.winfo_reqheight() <= canvas.winfo_height():
            return
        if event.num == 4:
            canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            canvas.yview_scroll(3, "units")
        else:
            delta = -1 * (event.delta // 120) if abs(event.delta) >= 120 else -event.delta
            canvas.yview_scroll(delta * 3, "units")

    canvas.bind("<Configure>", on_canvas_resize)
    page.bind("<Configure>", on_page_resize)
    root.bind_all("<MouseWheel>", scroll_page)
    root.bind_all("<Button-4>", scroll_page)
    root.bind_all("<Button-5>", scroll_page)
    root.after(150, monitor_page_height)

    ui.update({
        'clock_label': clock_label,
        'tagline_label': tagline_label,
        'canvas': canvas,
        'page': page,
        "page_window": page_window,
        'left_panel': left_panel,
        'right_panel': right_panel,
        "grid_container": grid_container,
        'stock_labels': stock_labels,
        'buy_buttons': buy_buttons,
        'product_cards': product_cards,
        'image_references': image_references,
        'product_image_labels': product_image_labels,
        "panel": panel,
        'order_details_frame': order_details_frame,
        'total_label': total_label,
        'notification_label': notification_label,
        'pay_button': pay_button,
        'cancel_button': cancel_button,
        'payment_status_label': payment_status_label,
        'system_status_labels': system_status_labels,
        'update_system_status': update_system_status,
        'qr_label': qr_label,
        'scan_label': scan_label,
        "qr_state": qr_state,
        'show_qr': show_qr,
        'show_empty_qr': show_empty_qr,
        'show_payment_link_qr': show_payment_link_qr,
        'display_qr_image': display_qr_image,
        'attach_hover': attach_hover,
        'update_products': update_products,
        'update_order': update_order,
        'show_success_screen': show_success_screen,
        'close_success_screen': close_success_screen,
        'success_screen': success_screen,
    })
    return ui
