try:
    from .amazon_label_renderer import (
        GAP_X_MM,
        LABEL_HEIGHT_MM,
        LABEL_WIDTH_MM,
        PAGE_HEIGHT_MM,
        PAGE_WIDTH_MM,
        build_amazon_label_payload,
        get_amazon_layout_positions,
    )
    from .amazon_rules import clean_text
    from .amazon_validation import parse_positive_int
except ImportError:
    from amazon_label_renderer import (
        GAP_X_MM,
        LABEL_HEIGHT_MM,
        LABEL_WIDTH_MM,
        PAGE_HEIGHT_MM,
        PAGE_WIDTH_MM,
        build_amazon_label_payload,
        get_amazon_layout_positions,
    )
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

DOTS_PER_MM = 8.0
BARCODE_HEIGHT_DOTS = 42


def dots(mm_value):
    return int(round(float(mm_value) * DOTS_PER_MM))


def tspl_escape(value):
    return clean_text(value).replace('"', "'")


def text_cmd(x, y, font, rotation, x_mul, y_mul, text):
    return f'TEXT {x},{y},"{font}",{rotation},{x_mul},{y_mul},"{tspl_escape(text)}"'


def barcode_cmd(x, y, value):
    return f'BARCODE {x},{y},"93",42,0,180,2,4,"{tspl_escape(value)}"'


def y_from_top(top_mm, adjust_dots=0):
    return dots(PAGE_HEIGHT_MM - top_mm) + int(adjust_dots)


def label_right_dots(side):
    left_mm = 0.0 if side == "left" else LABEL_WIDTH_MM + GAP_X_MM
    return dots(left_mm + LABEL_WIDTH_MM)


def x_from_left_mm(side, x_mm):
    right = label_right_dots(side)
    return right - dots(x_mm)


def text_fit(value, max_chars):
    value = clean_text(value)
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "."


def add_field(lines, side, y, label, value, positions):
    field_x = x_from_left_mm(side, positions["prn_field_label_anchor_x_mm"])
    colon_x = x_from_left_mm(side, positions["prn_field_colon_anchor_x_mm"])
    value_x = x_from_left_mm(side, positions["prn_field_value_anchor_x_mm"])
    lines.append(text_cmd(field_x, y, "0", 180, 4, 4, label))
    lines.append(text_cmd(colon_x, y, "0", 180, 4, 4, ":"))
    lines.append(text_cmd(value_x, y, "0", 180, 4, 4, text_fit(value, 42)))


def add_label(lines, row, branch, side):
    positions = get_amazon_layout_positions()
    payload = build_amazon_label_payload(row, branch)

    heading_x = x_from_left_mm(side, positions["prn_heading_anchor_x_mm"])
    field_x = x_from_left_mm(side, positions["prn_body_text_anchor_x_mm"])
    barcode_x = x_from_left_mm(side, positions["barcode_margin_x_mm"])
    barcode_text_x = x_from_left_mm(side, positions["prn_barcode_text_anchor_x_mm"])
    title_x = x_from_left_mm(side, positions["prn_title_anchor_x_mm"])

    lines.append(text_cmd(heading_x, y_from_top(positions["heading_top_mm"], positions["prn_heading_y_adjust_dots"]), "0", 180, 13, 9, payload["heading"]))

    for index, (label, value) in enumerate(payload["field_rows"]):
        y = y_from_top(positions["field_top_mm"] + index * positions["field_gap_mm"], positions["prn_field_y_adjust_dots"])
        add_field(lines, side, y, label, value, positions)

    lines.append(
        text_cmd(
            field_x,
            y_from_top(positions["care_top_mm"], positions["prn_care_y_adjust_dots"]),
            "0",
            180,
            3,
            4,
            payload["care_heading"],
        )
    )

    barcode_top_mm = LABEL_HEIGHT_MM - positions["barcode_bottom_mm"] - positions["barcode_height_mm"]
    max_address_top = barcode_top_mm - positions["address_stop_before_barcode_mm"]
    for index, line in enumerate(payload["address_lines"]):
        top_mm = positions["address_top_mm"] + index * positions["address_gap_mm"]
        if top_mm > max_address_top:
            break
        lines.append(text_cmd(field_x, y_from_top(top_mm, positions["prn_address_y_adjust_dots"]), "0", 180, 3, 4, text_fit(line, 48)))

    barcode_y = dots(positions["barcode_bottom_mm"]) + BARCODE_HEIGHT_DOTS
    lines.append(barcode_cmd(barcode_x, barcode_y, payload["fnsku"]))
    lines.append(text_cmd(barcode_text_x, dots(positions["barcode_text_bottom_mm"]) + positions["prn_barcode_text_y_adjust_dots"], "ROMAN.TTF", 180, 1, 8, payload["fnsku"]))
    lines.append(text_cmd(title_x, dots(positions["title_bottom_mm"]) + positions["prn_title_y_adjust_dots"], "0", 180, 5, 6, payload["title"]))


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
