from amazon_rules import clean_text
from amazon_validation import format_mrp, parse_positive_int

try:
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.lib.units import mm
    from reportlab.graphics.barcode import code128
except Exception:
    pdfcanvas = None
    mm = 2.834645669291339
    code128 = None


def safe_float(value, default):
    try:
        return float(str(value).strip())
    except Exception:
        return default


def wrap_text(text, max_chars):
    text = clean_text(text)
    if not text:
        return []
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        if len(cur) + len(word) + (1 if cur else 0) <= max_chars:
            cur = (cur + " " + word).strip()
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def amazon_title_for_print(title):
    return f"{clean_text(title)[:50].strip()} New".strip()


def branch_address_lines(branch):
    origin = clean_text(branch.get("origin", "")) or "Country of Origin: India"
    lines = [
        "Manufactured by / Marketed by:",
        clean_text(branch.get("marketed_by", "")),
        clean_text(branch.get("address", "")),
        f"Email: {clean_text(branch.get('email', ''))}",
        f"Contact: {clean_text(branch.get('phone', ''))}",
        origin,
    ]
    return [line for line in lines if clean_text(line) and not line.endswith(": ")]


def draw_wrapped(c, x, yy, max_y_bottom, text, font_name, font_size, max_chars, leading_mm, max_lines=None):
    c.setFont(font_name, font_size)
    count = 0
    for part in wrap_text(text, max_chars):
        if yy < max_y_bottom:
            break
        if max_lines is not None and count >= max_lines:
            break
        c.drawString(x, yy, part)
        yy -= leading_mm * mm
        count += 1
    return yy


def draw_amazon_pdf_label(c, x, y, w, h, row, branch):
    c.rect(x, y, w, h, stroke=1, fill=0)

    heading = clean_text(row.get("main_heading", ""))
    brand = clean_text(row.get("brand", ""))
    sku = clean_text(row.get("merchant_sku", ""))
    fnsku = clean_text(row.get("fnsku", ""))
    generic = clean_text(row.get("generic_name", "")) or heading
    title = amazon_title_for_print(row.get("title", ""))
    mrp_line = format_mrp(row.get("mrp", ""))

    title_font = 7.6
    brand_font = 5.35
    body_font = 4.45
    address_font = 3.72
    address_title_font = 3.95

    c.setFont("Helvetica-Bold", title_font)
    c.drawCentredString(x + w / 2, y + h - 3.0 * mm, heading[:34])
    c.setFont("Helvetica-Bold", brand_font)
    c.drawCentredString(x + w / 2, y + h - 5.45 * mm, brand[:42])
    c.setLineWidth(0.45)
    c.line(x + 2.2 * mm, y + h - 6.65 * mm, x + w - 2.2 * mm, y + h - 6.65 * mm)

    barcode_text_y = y + 0.95 * mm
    barcode_y = y + 2.55 * mm
    barcode_h = 6.45 * mm
    barcode_top = barcode_y + barcode_h
    address_bottom = barcode_top + 1.10 * mm

    yy = y + h - 8.35 * mm
    product_bottom = y + 24.0 * mm
    product_lines = [
        f"SKU No: {sku}",
        "Net Quantity: 1 N",
        mrp_line,
        f"Generic Name: {generic}",
        f"Title: {title}",
    ]
    for i, line in enumerate(product_lines):
        if not clean_text(line):
            continue
        max_chars = 47 if i != 4 else 45
        max_lines = 1 if i < 4 else 2
        yy = draw_wrapped(c, x + 2.5 * mm, yy, product_bottom, line, "Helvetica", body_font, max_chars, 1.43, max_lines=max_lines)
        yy -= 0.06 * mm

    yy = min(yy - 0.7 * mm, y + 22.0 * mm)
    yy = max(yy, y + 17.7 * mm)
    for i, line in enumerate(branch_address_lines(branch)):
        is_title = i == 0
        font_name = "Helvetica-Bold" if is_title else "Helvetica"
        font_size = address_title_font if is_title else address_font
        max_chars = 48 if is_title else 50
        indent = 2.5 if is_title else 3.3
        yy = draw_wrapped(c, x + indent * mm, yy, address_bottom, line, font_name, font_size, max_chars, 1.21, max_lines=2 if i in (1, 2) else 1)
        if is_title:
            yy -= 0.10 * mm

    if code128 is not None and fnsku:
        try:
            target_w = w - 4.5 * mm
            bc = code128.Code128(fnsku, barHeight=barcode_h, barWidth=0.235 * mm, humanReadable=False)
            if bc.width > target_w:
                bw = bc.barWidth * (target_w / bc.width)
                bc = code128.Code128(fnsku, barHeight=barcode_h, barWidth=bw, humanReadable=False)
            bc.drawOn(c, x + (w - bc.width) / 2, barcode_y)
        except Exception:
            c.setFont("Helvetica", 4)
            c.drawCentredString(x + w / 2, y + 5.0 * mm, "BARCODE ERROR")

    c.setFont("Helvetica", 4.35)
    c.drawCentredString(x + w / 2, barcode_text_y, fnsku)


def generate_amazon_pdf(out, rows, branch, progress_callback=None):
    if pdfcanvas is None:
        raise RuntimeError("reportlab missing. Run install_requirements.bat.")
    label_w_mm = safe_float(branch.get("roll_label_width_mm", "50.0"), 50.0)
    label_h_mm = safe_float(branch.get("roll_label_height_mm", "50.0"), 50.0)
    page_w_mm = safe_float(branch.get("roll_page_width_mm", "106.0"), 106.0)
    gap_x_mm = safe_float(branch.get("roll_gap_x_mm", "3.0"), 3.0)
    auto_margin_x_mm = max(0.0, (page_w_mm - (label_w_mm * 2) - gap_x_mm) / 2.0)
    margin_x_mm = safe_float(branch.get("roll_margin_x_mm", str(auto_margin_x_mm)), auto_margin_x_mm)

    label_w = label_w_mm * mm
    label_h = label_h_mm * mm
    page_w = page_w_mm * mm
    page_h = label_h
    gap_x = gap_x_mm * mm
    margin_x = margin_x_mm * mm

    total = sum(parse_positive_int(row.get("print_qty", 0)) for row in rows)
    c = pdfcanvas.Canvas(str(out), pagesize=(page_w, page_h), pageCompression=1)
    done = 0
    col = 0
    for row in rows:
        qty = parse_positive_int(row.get("print_qty", 0))
        for _ in range(qty):
            x = margin_x + col * (label_w + gap_x)
            draw_amazon_pdf_label(c, x, 0, label_w, label_h, row, branch)
            done += 1
            if progress_callback and (done == total or done % 100 == 0):
                progress_callback(done, total)
            col += 1
            if col >= 2:
                col = 0
                if done < total:
                    c.showPage()
    c.save()
    return total
