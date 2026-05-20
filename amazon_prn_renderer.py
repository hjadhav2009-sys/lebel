from amazon_label_renderer import amazon_mrp_for_print, amazon_title_for_print, branch_origin_for_print, wrap_text
from amazon_rules import clean_text
from amazon_validation import parse_positive_int


HEADER = [
    "SIZE 101.5 mm, 50 mm",
    "GAP 3 mm, 0 mm",
    "SET RIBBON OFF",
    "DIRECTION 0,0",
    "REFERENCE 0,0",
    "OFFSET 0 mm",
    "SET PEEL OFF",
    "SET CUTTER OFF",
    "SET PARTIAL_CUTTER OFF",
    "SET TEAR ON",
    "CLS",
    "CODEPAGE 1252",
]


def tspl_escape(value):
    return clean_text(value).replace('"', "'")


def text_cmd(x, y, font, rotation, x_mul, y_mul, text):
    return f'TEXT {x},{y},"{font}",{rotation},{x_mul},{y_mul},"{tspl_escape(text)}"'


def barcode_cmd(x, y, value):
    return f'BARCODE {x},{y},"93",42,0,180,2,4,"{tspl_escape(value)}"'


def split_address(branch):
    lines = []
    for raw in (branch.get("marketed_by", ""), branch.get("address", "")):
        for line in wrap_text(raw, 34):
            if line:
                lines.append(line)
    return lines[:3]


def label_payload(row, branch):
    heading = clean_text(row.get("main_heading", ""))
    brand = clean_text(row.get("brand", ""))
    sku = clean_text(row.get("merchant_sku", ""))
    generic = clean_text(row.get("generic_name", "")) or heading
    return {
        "heading": heading,
        "brand": brand,
        "sku": sku,
        "qty": "1 N",
        "mrp": amazon_mrp_for_print(row.get("mrp", "")),
        "generic": generic,
        "fnsku": clean_text(row.get("fnsku", "")),
        "title": amazon_title_for_print(row.get("title", "")),
        "address": split_address(branch),
        "email": f"Email Id:{clean_text(branch.get('email', ''))}",
        "contact": f"Contact:{clean_text(branch.get('phone', ''))}",
        "origin": f"Origin:{branch_origin_for_print(branch)}",
    }


def add_field(lines, x, y, label, value):
    lines.append(text_cmd(x, y, "0", 180, 5, 5, label))
    lines.append(text_cmd(x - 105, y, "0", 180, 5, 5, ":"))
    lines.append(text_cmd(x - 121, y, "0", 180, 5, 5, value))


def add_label(lines, row, branch, side):
    payload = label_payload(row, branch)
    if side == "left":
        title_x, field_x, barcode_x, barcode_text_x, bottom_x = 283, 367, 350, 288, 367
    else:
        title_x, field_x, barcode_x, barcode_text_x, bottom_x = 694, 778, 761, 699, 778

    lines.append(text_cmd(title_x, 374, "0", 180, 13, 9, f"{payload['heading']} "))
    add_field(lines, field_x, 334, "Brand", payload["brand"])
    add_field(lines, field_x, 309, "SKU No", payload["sku"])
    add_field(lines, field_x, 284, "Net Quantity", payload["qty"])
    add_field(lines, field_x, 259, "MRP", payload["mrp"])
    add_field(lines, field_x, 234, "Generic Name", payload["generic"])

    lines.append(text_cmd(field_x, 207, "0", 180, 4, 5, "Manufactured by / Marketed By / Customer care Details:"))
    y = 186
    for addr in payload["address"]:
        lines.append(text_cmd(field_x, y, "0", 180, 4, 5, addr))
        y -= 17
    lines.append(text_cmd(field_x, y, "0", 180, 4, 5, payload["email"]))
    y -= 17
    lines.append(text_cmd(field_x, y, "0", 180, 4, 5, payload["contact"]))
    y -= 17
    lines.append(text_cmd(field_x, y, "0", 180, 4, 5, payload["origin"]))

    lines.append(barcode_cmd(barcode_x, 109, payload["fnsku"]))
    lines.append(text_cmd(barcode_text_x, 63, "ROMAN.TTF", 180, 1, 8, payload["fnsku"]))
    lines.append(text_cmd(bottom_x, 37, "0", 180, 5, 6, payload["title"]))


def expanded_rows(rows):
    for row in rows:
        for _ in range(parse_positive_int(row.get("print_qty", 0))):
            yield row


def generate_amazon_prn(out, rows, branch, progress_callback=None):
    labels = list(expanded_rows(rows))
    total = len(labels)
    out_lines = []
    done = 0
    for idx in range(0, total, 2):
        out_lines.extend(HEADER)
        add_label(out_lines, labels[idx], branch, "left")
        done += 1
        if idx + 1 < total:
            add_label(out_lines, labels[idx + 1], branch, "right")
            done += 1
        out_lines.append("PRINT 1,1")
        if progress_callback and (done == total or done % 100 == 0):
            progress_callback(done, total)
    with open(out, "w", encoding="cp1252", errors="replace", newline="\r\n") as f:
        f.write("\n".join(out_lines))
        f.write("\n")
    return total
