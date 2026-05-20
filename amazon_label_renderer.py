from amazon_rules import clean_text
from amazon_validation import normalize_mrp, parse_positive_int

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


def amazon_display_heading(category):
    category = clean_text(category)
    names = {
        "Pendant Necklace": "Pendant",
        "Keychain": "Keychain",
        "Bracelet": "Bracelet",
        "Ring": "Ring",
        "Earring": "Earring",
        "Brooch": "Brooch",
        "Car Hanger": "Car Hanger",
        "Dashbord": "Dashbord",
    }
    return names.get(category, category)


def amazon_mrp_for_print(value):
    mrp = normalize_mrp(value)
    return f"Rs.{mrp} (inclusive of all Taxes)" if mrp else ""


def branch_origin_for_print(branch):
    origin = clean_text(branch.get("origin", "")) or "Country of Origin: India"
    if ":" in origin:
        origin = origin.split(":", 1)[1]
    return clean_text(origin) or "India"


def branch_address_lines(branch):
    lines = [
        clean_text(branch.get("marketed_by", "")),
        clean_text(branch.get("address", "")),
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


def draw_label_value(c, x, y, label, value, colon_x, value_x, font_size=3.9):
    c.setFont("Helvetica-Bold", font_size)
    c.drawString(x, y, label)
    c.setFont("Helvetica", font_size)
    c.drawString(colon_x, y, ":")
    c.drawString(value_x, y, clean_text(value))


def draw_amazon_pdf_label(c, x, y, w, h, row, branch):
    c.rect(x, y, w, h, stroke=1, fill=0)

    heading = amazon_display_heading(row.get("main_heading", ""))
    brand = clean_text(row.get("brand", ""))
    sku = clean_text(row.get("merchant_sku", ""))
    fnsku = clean_text(row.get("fnsku", ""))
    generic = amazon_display_heading(row.get("generic_name", "")) or heading
    title = amazon_title_for_print(row.get("title", ""))
    mrp_line = amazon_mrp_for_print(row.get("mrp", ""))

    top_y = y + 45.0 * mm
    c.setFont("Helvetica-Bold", 7.2)
    c.drawCentredString(x + w / 2, top_y, heading[:26])

    yy = y + 41.0 * mm
    row_gap = 1.75 * mm
    left_x = x + 2.2 * mm
    colon_x = x + 16.0 * mm
    value_x = x + 17.2 * mm
    value_rows = [
        ("Brand", brand),
        ("SKU No", sku),
        ("Net Quantity", "1 N"),
        ("MRP", mrp_line),
        ("Generic Name", generic),
    ]
    for label, value in value_rows:
        draw_label_value(c, left_x, yy, label, value, colon_x, value_x, font_size=3.9)
        yy -= row_gap

    heading_line_y = yy - 1.0 * mm
    c.setFont("Helvetica-Bold", 3.8)
    care_text = "Manufactured by / Marketed By / Customer care Details:"
    c.drawString(left_x, heading_line_y, care_text)
    c.setLineWidth(0.3)
    c.line(x + 1.8 * mm, heading_line_y - 0.45 * mm, x + w - 1.8 * mm, heading_line_y - 0.45 * mm)

    address_y = heading_line_y - 2.1 * mm
    c.setFont("Helvetica", 3.55)
    for line in branch_address_lines(branch):
        for part in wrap_text(line, 42)[:2]:
            if address_y < y + 14.0 * mm:
                break
            c.drawString(left_x, address_y, part)
            address_y -= 1.45 * mm

    for line in [
        f"Email Id:{clean_text(branch.get('email', ''))}",
        f"Contact:{clean_text(branch.get('phone', ''))}",
        f"Origin:{branch_origin_for_print(branch)}",
    ]:
        if address_y < y + 14.0 * mm:
            break
        c.drawString(left_x, address_y, line)
        address_y -= 1.45 * mm

    barcode_y = y + 6.8 * mm
    barcode_h = 6.6 * mm
    barcode_text_y = y + 4.0 * mm
    title_y = y + 1.4 * mm

    if code128 is not None and fnsku:
        try:
            target_w = w - 12.0 * mm
            bc = code128.Code128(fnsku, barHeight=barcode_h, barWidth=0.22 * mm, humanReadable=False)
            if bc.width > target_w:
                bw = bc.barWidth * (target_w / bc.width)
                bc = code128.Code128(fnsku, barHeight=barcode_h, barWidth=bw, humanReadable=False)
            bc.drawOn(c, x + (w - bc.width) / 2, barcode_y)
        except Exception:
            c.setFont("Helvetica", 4)
            c.drawCentredString(x + w / 2, y + 5.0 * mm, "BARCODE ERROR")

    c.setFont("Helvetica", 4.4)
    c.drawCentredString(x + w / 2, barcode_text_y, fnsku)
    c.setFont("Helvetica", 3.65)
    c.drawCentredString(x + w / 2, title_y, title[:58])


def generate_amazon_pdf(out, rows, branch, progress_callback=None):
    if pdfcanvas is None:
        raise RuntimeError("reportlab missing. Run install_requirements.bat.")
    label_w_mm = 49.8
    label_h_mm = 49.8
    page_w_mm = 101.5
    page_h_mm = 50.0
    gap_x_mm = 101.5 - (49.8 * 2)
    auto_margin_x_mm = max(0.0, (page_w_mm - (label_w_mm * 2) - gap_x_mm) / 2.0)
    margin_x_mm = auto_margin_x_mm

    label_w = label_w_mm * mm
    label_h = label_h_mm * mm
    page_w = page_w_mm * mm
    page_h = page_h_mm * mm
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
            draw_amazon_pdf_label(c, x, (page_h - label_h) / 2, label_w, label_h, row, branch)
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
