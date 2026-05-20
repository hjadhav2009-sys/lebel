"""
label_generator.py  v4
- Courier name shown in black bar (replaces CUSTOM ORDER banner)
- CUSTOM ORDER and CUSTOMISATION removed from label (data still in CSV)
- Bigger, bolder company name in header, proper logo alignment
- Bold ship-to address for delivery partner visibility
- FROM section fully customisable per branch profile
- Branch logo support
- Clean professional layout
"""

import os, sys, re
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm, inch
from reportlab.lib.utils import simpleSplit
from reportlab.lib import colors

LABEL_W = 4 * inch
LABEL_H = 6 * inch

C_BLACK = colors.black
C_DARK  = colors.HexColor("#111111")
C_MID   = colors.HexColor("#555555")
C_LIGHT = colors.HexColor("#999999")
C_WHITE = colors.white
C_RULE  = colors.HexColor("#CCCCCC")


def _base():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.abspath(".")


def clean(t):
    return re.sub(r'\s+', ' ', str(t)).strip()


def rs(t):
    return str(t).replace('\u20b9', 'Rs.').replace('Rs.', 'Rs.')


def draw_label(c, order, x0=0, y0=0):
    W, H = LABEL_W, LABEL_H
    ml   = 7 * mm
    mr   = 7 * mm
    iw   = W - ml - mr

    # Resolve logo: prefer branch logo, fallback to default assets/logo.png
    branch_logo = order.get('branch_logo_path', '')
    if branch_logo and os.path.exists(branch_logo):
        logo_path = branch_logo
    else:
        logo_path = os.path.join(_base(), "assets", "logo.png")

    brand_name  = order.get('brand_name', 'SUJAL FASHION WORKS').upper()
    courier     = order.get('courier', '').strip()

    # ── Outer border ─────────────────────────────────────────
    c.setStrokeColor(C_DARK)
    c.setLineWidth(1.5)
    c.rect(x0 + 2, y0 + 2, W - 4, H - 4)

    # ── Header block ─────────────────────────────────────────
    HDR_H   = 20 * mm          # taller header for breathing room
    hdr_top = y0 + H - 4
    hdr_bot = hdr_top - HDR_H

    c.setFillColor(C_DARK)
    c.rect(x0 + 2, hdr_bot, W - 4, HDR_H, stroke=0, fill=1)

    # Logo — left side, vertically centred
    logo_h = 11 * mm
    logo_w = 26 * mm
    logo_y = hdr_bot + (HDR_H - logo_h) / 2

    logo_drawn = False
    if os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, x0 + ml, logo_y,
                        width=logo_w, height=logo_h,
                        preserveAspectRatio=True, mask='auto')
            logo_drawn = True
        except Exception:
            pass

    # Company name — right of logo, big and bold
    text_x = x0 + ml + (logo_w + 4 * mm if logo_drawn else 0)
    text_avail = W - mr - (text_x - x0)

    # Brand name — large
    c.setFillColor(C_WHITE)
    # Auto-fit brand name size
    font_size = 11
    while font_size > 7:
        if c.stringWidth(brand_name, "Helvetica-Bold", font_size) <= text_avail:
            break
        font_size -= 0.5

    brand_y = hdr_bot + HDR_H * 0.60
    c.setFont("Helvetica-Bold", font_size)
    c.drawString(text_x, brand_y, brand_name)

    # "SHIPPING LABEL" subtitle
    c.setFillColor(C_LIGHT)
    c.setFont("Helvetica", 6.5)
    c.drawString(text_x, hdr_bot + HDR_H * 0.25, "SHIPPING LABEL")

    # ── Courier bar ──────────────────────────────────────────
    COU_H = 0
    if courier:
        COU_H   = 7 * mm
        cb_top  = hdr_bot
        cb_bot  = cb_top - COU_H

        c.setFillColor(C_DARK)
        c.rect(x0 + 2, cb_bot, W - 4, COU_H, stroke=0, fill=1)

        c.setStrokeColor(C_WHITE)
        c.setLineWidth(0.4)
        c.line(x0 + 2, cb_top, x0 + W - 2, cb_top)
        c.line(x0 + 2, cb_bot, x0 + W - 2, cb_bot)

        c.setFillColor(C_WHITE)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(x0 + W / 2, cb_bot + 2.2 * mm,
                            courier.upper())

    # ── Body cursor ──────────────────────────────────────────
    y = hdr_bot - COU_H - 5 * mm

    # ── Helpers ──────────────────────────────────────────────

    def gap(n=2.0):
        nonlocal y
        y -= n * mm

    def divider():
        nonlocal y
        y -= 2.5 * mm
        c.setStrokeColor(C_RULE)
        c.setLineWidth(0.3)
        c.setDash(2, 4)
        c.line(x0 + ml, y, x0 + W - mr, y)
        c.setDash()
        y -= 3 * mm

    def sec(title):
        nonlocal y
        c.setFillColor(C_MID)
        c.setFont("Helvetica-Bold", 6)
        c.drawString(x0 + ml, y, title.upper())
        y -= 4.5 * mm

    def write(text, size=8, bold=False, col=None, indent=0):
        nonlocal y
        fn = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(fn, size)
        c.setFillColor(col if col is not None else C_BLACK)
        for line in simpleSplit(str(text), fn, size, iw - indent):
            c.drawString(x0 + ml + indent, y, line)
            y -= (size + 2.5)

    def kv(key, val, size=7.5, val_bold=False):
        nonlocal y
        lbl = f"{key}:"
        c.setFillColor(C_MID)
        c.setFont("Helvetica-Bold", size)
        c.drawString(x0 + ml, y, lbl)
        kw = c.stringWidth(lbl + " ", "Helvetica-Bold", size)
        fn = "Helvetica-Bold" if val_bold else "Helvetica"
        c.setFillColor(C_BLACK)
        c.setFont(fn, size)
        val_s = rs(str(val))
        lines = simpleSplit(val_s, fn, size, iw - kw)
        if lines:
            c.drawString(x0 + ml + kw, y, lines[0])
        y -= (size + 2.5)
        for ex in lines[1:]:
            c.drawString(x0 + ml + kw, y, ex)
            y -= (size + 2.5)

    # ═══════════════════════════════════════════
    # SHIP TO
    # ═══════════════════════════════════════════
    sec("Ship To")

    # Customer name — large and prominent
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(C_DARK)
    c.drawString(x0 + ml, y, order.get('ship_name', ''))
    y -= 7 * mm

    # Address — BOLD for delivery partner visibility
    addr_text = order.get('ship_address', '')
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(C_BLACK)
    for line in simpleSplit(addr_text, "Helvetica-Bold", 8.5, iw):
        c.drawString(x0 + ml, y, line)
        y -= (8.5 + 2.5)

    gap(0.5)

    # Phone — bold
    phone = order.get('ship_phone', '')
    if phone:
        kv("Phone", phone, size=8.5, val_bold=True)

    divider()

    # ═══════════════════════════════════════════
    # FROM  (fully customisable per branch)
    # ═══════════════════════════════════════════
    sec("From")
    from_addr = order.get('from_address', '')
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(C_MID)
    for line in from_addr.split('\n'):
        line = line.strip()
        if line:
            for sub in simpleSplit(line, "Helvetica-Bold", 7.5, iw):
                c.drawString(x0 + ml, y, sub)
                y -= (7.5 + 2.5)

    divider()

    # ═══════════════════════════════════════════
    # ORDER DETAILS
    # ═══════════════════════════════════════════
    sec("Order Details")
    kv("Order ID", order.get('order_id', ''),    size=7.5)
    kv("Date",     order.get('order_date', ''),  size=7.5)
    kv("Amount",   order.get('grand_total', ''), size=7.5)

    divider()

    # ═══════════════════════════════════════════
    # PRODUCT
    # ═══════════════════════════════════════════
    sec("Product")

    product = order.get('product_name', '')
    product = re.sub(r'PM Amazon.*', '', product, flags=re.IGNORECASE)
    product = re.sub(r'Quantity.*',  '', product, flags=re.IGNORECASE)
    product = clean(product)

    write(product, bold=True, size=8, col=C_DARK)
    gap(1.0)
    kv("SKU",  order.get('sku', ''),  size=7.5)
    kv("ASIN", order.get('asin', ''), size=7.5)
    kv("Qty",  order.get('qty', '1'), size=7.5)

    # ── Footer ───────────────────────────────────────────────
    fy = y0 + 4 * mm
    c.setStrokeColor(C_RULE)
    c.setLineWidth(0.3)
    c.line(x0 + ml, fy + 4.5 * mm, x0 + W - mr, fy + 4.5 * mm)
    c.setFillColor(C_LIGHT)
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(
        x0 + W / 2, fy + 1.5 * mm,
        f"Order: {order.get('order_id', '')}   SKU: {order.get('sku', '')}   Qty: {order.get('qty', '1')}"
    )


def generate_labels_pdf(orders, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    c = canvas.Canvas(output_path, pagesize=(LABEL_W, LABEL_H))
    for order in orders:
        try:
            draw_label(c, order, x0=0, y0=0)
            c.showPage()
        except Exception as e:
            print(f"[Label Error] {order.get('order_id', '?')} - {e}")
            c.showPage()
    c.save()
    print(f"[OK] Labels saved -> {output_path}  ({len(orders)} pages)")