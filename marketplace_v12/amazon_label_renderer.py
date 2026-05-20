import copy

try:
    from .amazon_rules import clean_text
    from .amazon_validation import normalize_mrp, parse_positive_int
except ImportError:
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


PDF_LAYOUT_BARTENDER = "BarTender 2UP 101.5x50"
PDF_LAYOUT_SINGLE = "Single Label Preview 49.8x49.8"
PDF_LAYOUT_VALUES = [PDF_LAYOUT_BARTENDER, PDF_LAYOUT_SINGLE]

LABEL_WIDTH_MM = 49.8
LABEL_HEIGHT_MM = 49.8
PAGE_WIDTH_MM = 101.5
PAGE_HEIGHT_MM = 50.0
GAP_X_MM = 1.9

LAYOUT_POSITIONS = {
    "margin_left_mm": 2.2,
    "margin_right_mm": 1.8,
    "heading_top_mm": 4.1,
    "heading_font": 7.1,
    "field_top_mm": 8.1,
    "field_gap_mm": 1.95,
    "field_label_font": 3.85,
    "field_value_font": 3.75,
    "field_label_x_mm": 2.2,
    "field_colon_x_mm": 16.0,
    "field_value_x_mm": 17.2,
    "care_top_mm": 19.2,
    "care_font": 3.65,
    "care_underline_offset_mm": 0.42,
    "address_top_mm": 21.15,
    "address_gap_mm": 1.5,
    "address_font": 3.45,
    "address_stop_before_barcode_mm": 1.1,
    "barcode_bottom_mm": 7.6,
    "barcode_height_mm": 6.7,
    "barcode_margin_x_mm": 6.0,
    "barcode_text_bottom_mm": 4.35,
    "barcode_text_font": 4.25,
    "title_bottom_mm": 1.35,
    "title_font": 3.55,
}


def normalize_pdf_layout(layout):
    if layout == PDF_LAYOUT_SINGLE:
        return PDF_LAYOUT_SINGLE
    return PDF_LAYOUT_BARTENDER


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


def fit_text(text, max_chars):
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "."


def amazon_title_for_print(title):
    base = clean_text(title)[:50].strip()
    return f"{base} New".strip()


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
        clean_text(branch.get("marketed_by", "") or branch.get("company", "")),
        clean_text(branch.get("address", "")),
    ]
    return [line for line in lines if clean_text(line) and not line.endswith(": ")]


def build_address_lines(branch):
    lines = []
    for raw in branch_address_lines(branch):
        lines.extend(wrap_text(raw, 42)[:2])
    lines.extend(
        [
            f"Email Id:{clean_text(branch.get('email', ''))}",
            f"Contact:{clean_text(branch.get('phone', ''))}",
            f"Origin:{branch_origin_for_print(branch)}",
        ]
    )
    return [fit_text(line, 48) for line in lines if clean_text(line)]


def build_amazon_label_payload(row, branch):
    heading = amazon_display_heading(row.get("main_heading", ""))
    generic = amazon_display_heading(row.get("generic_name", "")) or heading
    return {
        "heading": fit_text(heading, 28),
        "field_rows": [
            ("Brand", fit_text(row.get("brand", ""), 30)),
            ("SKU No", fit_text(row.get("merchant_sku", ""), 30)),
            ("Net Quantity", "1 N"),
            ("MRP", fit_text(amazon_mrp_for_print(row.get("mrp", "")), 42)),
            ("Generic Name", fit_text(generic, 30)),
        ],
        "care_heading": "Manufactured by / Marketed By / Customer care Details:",
        "address_lines": build_address_lines(branch),
        "fnsku": clean_text(row.get("fnsku", "")),
        "title": fit_text(amazon_title_for_print(row.get("title", "")), 58),
    }


def get_amazon_layout_positions():
    return copy.deepcopy(LAYOUT_POSITIONS)


def _pdf_y(label_y, label_h, top_mm=None, bottom_mm=None):
    if bottom_mm is not None:
        return label_y + bottom_mm * mm
    return label_y + label_h - top_mm * mm


def _pdf_x(label_x, x_mm):
    return label_x + x_mm * mm


def draw_label_value_pdf(c, label_x, label_y, label_h, label, value, top_mm, positions):
    y = _pdf_y(label_y, label_h, top_mm=top_mm)
    c.setFont("Helvetica-Bold", positions["field_label_font"])
    c.drawString(_pdf_x(label_x, positions["field_label_x_mm"]), y, label)
    c.setFont("Helvetica", positions["field_value_font"])
    c.drawString(_pdf_x(label_x, positions["field_colon_x_mm"]), y, ":")
    c.drawString(_pdf_x(label_x, positions["field_value_x_mm"]), y, clean_text(value))


def draw_amazon_label_pdf(c, label_x, label_y, label_w, label_h, row, branch):
    positions = get_amazon_layout_positions()
    payload = build_amazon_label_payload(row, branch)

    c.rect(label_x, label_y, label_w, label_h, stroke=1, fill=0)

    c.setFont("Helvetica-Bold", positions["heading_font"])
    c.drawCentredString(
        label_x + label_w / 2,
        _pdf_y(label_y, label_h, top_mm=positions["heading_top_mm"]),
        payload["heading"],
    )

    for index, (label, value) in enumerate(payload["field_rows"]):
        draw_label_value_pdf(
            c,
            label_x,
            label_y,
            label_h,
            label,
            value,
            positions["field_top_mm"] + index * positions["field_gap_mm"],
            positions,
        )

    care_y = _pdf_y(label_y, label_h, top_mm=positions["care_top_mm"])
    left_x = _pdf_x(label_x, positions["margin_left_mm"])
    right_x = label_x + label_w - positions["margin_right_mm"] * mm
    c.setFont("Helvetica-Bold", positions["care_font"])
    c.drawString(left_x, care_y, payload["care_heading"])
    c.setLineWidth(0.3)
    c.line(left_x, care_y - positions["care_underline_offset_mm"] * mm, right_x, care_y - positions["care_underline_offset_mm"] * mm)

    c.setFont("Helvetica", positions["address_font"])
    barcode_top_mm = LABEL_HEIGHT_MM - positions["barcode_bottom_mm"] - positions["barcode_height_mm"]
    max_address_top = barcode_top_mm - positions["address_stop_before_barcode_mm"]
    for index, line in enumerate(payload["address_lines"]):
        top_mm = positions["address_top_mm"] + index * positions["address_gap_mm"]
        if top_mm > max_address_top:
            break
        c.drawString(left_x, _pdf_y(label_y, label_h, top_mm=top_mm), line)

    barcode_y = _pdf_y(label_y, label_h, bottom_mm=positions["barcode_bottom_mm"])
    barcode_h = positions["barcode_height_mm"] * mm
    barcode_margin = positions["barcode_margin_x_mm"] * mm
    if code128 is not None and payload["fnsku"]:
        try:
            target_w = label_w - (2 * barcode_margin)
            bc = code128.Code128(payload["fnsku"], barHeight=barcode_h, barWidth=0.22 * mm, humanReadable=False)
            if bc.width > target_w:
                bc = code128.Code128(payload["fnsku"], barHeight=barcode_h, barWidth=bc.barWidth * (target_w / bc.width), humanReadable=False)
            bc.drawOn(c, label_x + (label_w - bc.width) / 2, barcode_y)
        except Exception:
            c.setFont("Helvetica", 4)
            c.drawCentredString(label_x + label_w / 2, barcode_y + 2 * mm, "BARCODE ERROR")

    c.setFont("Helvetica", positions["barcode_text_font"])
    c.drawCentredString(label_x + label_w / 2, _pdf_y(label_y, label_h, bottom_mm=positions["barcode_text_bottom_mm"]), payload["fnsku"])
    c.setFont("Helvetica", positions["title_font"])
    c.drawCentredString(label_x + label_w / 2, _pdf_y(label_y, label_h, bottom_mm=positions["title_bottom_mm"]), payload["title"])


def _preview_font(points, scale, bold=False):
    size = max(6, int(round(points * scale / 2.834645669291339)))
    return ("Arial", size, "bold" if bold else "normal")


def _preview_x(label_x, scale, x_mm):
    return label_x + x_mm * scale


def _preview_y(label_y, scale, top_mm=None, bottom_mm=None):
    if bottom_mm is not None:
        return label_y + (LABEL_HEIGHT_MM - bottom_mm) * scale
    return label_y + top_mm * scale


def _draw_preview_barcode(canvas, x0, y0, x1, y1, value):
    canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="")
    seed = sum(ord(ch) for ch in clean_text(value)) or 17
    x = x0
    idx = 0
    while x < x1:
        width = 1 + ((seed + idx * 7) % 3)
        gap = 1 + ((seed + idx * 5) % 2)
        canvas.create_rectangle(x, y0, min(x + width, x1), y1, fill="#111111", outline="#111111")
        x += width + gap
        idx += 1


def draw_amazon_label_preview(canvas, label_x, label_y, label_size_px, row, branch):
    positions = get_amazon_layout_positions()
    payload = build_amazon_label_payload(row, branch)
    scale = label_size_px / LABEL_WIDTH_MM
    label_w = LABEL_WIDTH_MM * scale
    label_h = LABEL_HEIGHT_MM * scale
    canvas.create_rectangle(label_x, label_y, label_x + label_w, label_y + label_h, fill="white", outline="#111111", width=2)

    canvas.create_text(
        label_x + label_w / 2,
        _preview_y(label_y, scale, top_mm=positions["heading_top_mm"]),
        text=payload["heading"],
        anchor="s",
        fill="#111111",
        font=_preview_font(positions["heading_font"], scale, bold=True),
    )

    for index, (label, value) in enumerate(payload["field_rows"]):
        top_mm = positions["field_top_mm"] + index * positions["field_gap_mm"]
        yy = _preview_y(label_y, scale, top_mm=top_mm)
        canvas.create_text(
            _preview_x(label_x, scale, positions["field_label_x_mm"]),
            yy,
            text=label,
            anchor="sw",
            fill="#111111",
            font=_preview_font(positions["field_label_font"], scale, bold=True),
        )
        canvas.create_text(
            _preview_x(label_x, scale, positions["field_colon_x_mm"]),
            yy,
            text=":",
            anchor="sw",
            fill="#111111",
            font=_preview_font(positions["field_value_font"], scale),
        )
        canvas.create_text(
            _preview_x(label_x, scale, positions["field_value_x_mm"]),
            yy,
            text=value,
            anchor="sw",
            fill="#111111",
            font=_preview_font(positions["field_value_font"], scale),
        )

    care_y = _preview_y(label_y, scale, top_mm=positions["care_top_mm"])
    left_x = _preview_x(label_x, scale, positions["margin_left_mm"])
    right_x = label_x + label_w - positions["margin_right_mm"] * scale
    canvas.create_text(
        left_x,
        care_y,
        text=payload["care_heading"],
        anchor="sw",
        fill="#111111",
        font=_preview_font(positions["care_font"], scale, bold=True),
    )
    underline_y = care_y + positions["care_underline_offset_mm"] * scale
    canvas.create_line(left_x, underline_y, right_x, underline_y, fill="#111111")

    barcode_top_mm = LABEL_HEIGHT_MM - positions["barcode_bottom_mm"] - positions["barcode_height_mm"]
    max_address_top = barcode_top_mm - positions["address_stop_before_barcode_mm"]
    for index, line in enumerate(payload["address_lines"]):
        top_mm = positions["address_top_mm"] + index * positions["address_gap_mm"]
        if top_mm > max_address_top:
            break
        canvas.create_text(
            left_x,
            _preview_y(label_y, scale, top_mm=top_mm),
            text=line,
            anchor="sw",
            fill="#111111",
            font=_preview_font(positions["address_font"], scale),
        )

    barcode_left = label_x + positions["barcode_margin_x_mm"] * scale
    barcode_right = label_x + label_w - positions["barcode_margin_x_mm"] * scale
    barcode_bottom = label_y + label_h - positions["barcode_bottom_mm"] * scale
    barcode_top = barcode_bottom - positions["barcode_height_mm"] * scale
    _draw_preview_barcode(canvas, barcode_left, barcode_top, barcode_right, barcode_bottom, payload["fnsku"])
    canvas.create_text(
        label_x + label_w / 2,
        _preview_y(label_y, scale, bottom_mm=positions["barcode_text_bottom_mm"]),
        text=payload["fnsku"],
        anchor="s",
        fill="#111111",
        font=_preview_font(positions["barcode_text_font"], scale),
    )
    canvas.create_text(
        label_x + label_w / 2,
        _preview_y(label_y, scale, bottom_mm=positions["title_bottom_mm"]),
        text=payload["title"],
        anchor="s",
        fill="#111111",
        font=_preview_font(positions["title_font"], scale),
    )


def _expanded_rows(rows):
    for row in rows:
        for _ in range(parse_positive_int(row.get("print_qty", 0))):
            yield row


def generate_amazon_pdf(out, rows, branch, progress_callback=None, layout=PDF_LAYOUT_BARTENDER):
    if pdfcanvas is None:
        raise RuntimeError("reportlab missing. Run install_requirements.bat.")

    layout = normalize_pdf_layout(layout)
    label_w = LABEL_WIDTH_MM * mm
    label_h = LABEL_HEIGHT_MM * mm

    if layout == PDF_LAYOUT_SINGLE:
        page_w = LABEL_WIDTH_MM * mm
        page_h = LABEL_HEIGHT_MM * mm
        slots = [(0, 0)]
    else:
        page_w = PAGE_WIDTH_MM * mm
        page_h = PAGE_HEIGHT_MM * mm
        gap_x = GAP_X_MM * mm
        label_y = (page_h - label_h) / 2
        slots = [(0, label_y), (label_w + gap_x, label_y)]

    labels = list(_expanded_rows(rows))
    total = len(labels)
    c = pdfcanvas.Canvas(str(out), pagesize=(page_w, page_h), pageCompression=1)
    for index, row in enumerate(labels):
        slot_index = index % len(slots)
        if index and slot_index == 0:
            c.showPage()
        label_x, label_y = slots[slot_index]
        draw_amazon_label_pdf(c, label_x, label_y, label_w, label_h, row, branch)
        done = index + 1
        if progress_callback and (done == total or done % 100 == 0):
            progress_callback(done, total)
    c.save()
    return total


def generate_amazon_pdf_proof(out, row, branch, layout=PDF_LAYOUT_BARTENDER):
    proof_row = dict(row)
    proof_row["print_qty"] = 1
    return generate_amazon_pdf(out, [proof_row], branch, layout=layout)


def draw_amazon_pdf_label(c, x, y, w, h, row, branch):
    draw_amazon_label_pdf(c, x, y, w, h, row, branch)
