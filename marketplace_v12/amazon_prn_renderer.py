import sys
from pathlib import Path

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


BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
AMAZON_TEMPLATE_DIR = BASE_DIR / "reference_templates" / "amazon"
AMAZON_TEMPLATE_PATH = AMAZON_TEMPLATE_DIR / "amazon_template.prn"
AMAZON_TEMPLATE_MISSING_MESSAGE = (
    "Amazon BarTender template PRN missing. Place amazon_template.prn in "
    "marketplace_v12/reference_templates/amazon/"
)

PRN_MODE_TEMPLATE = "template_barcode_bitmap"
PRN_MODE_DYNAMIC = "dynamic_tspl"
PRN_MODE_VALUES = [PRN_MODE_TEMPLATE, PRN_MODE_DYNAMIC]

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

BARTENDER_COORDS = {
    "left": {
        "heading": (278, 385),
        "field": (355, 354),
        "barcode": (361, 122),
        "barcode_text": (300, 76),
        "title": (374, 48),
    },
    "right": {
        "heading": (689, 385),
        "field": (766, 354),
        "barcode": (772, 122),
        "barcode_text": (711, 76),
        "title": (785, 48),
    },
}
FIELD_ROW_GAP_DOTS = 16
CARE_HEADING_Y = 264
ADDRESS_START_Y = 244
ADDRESS_GAP_DOTS = 14
FIELD_LABEL_WIDTH = 16
MAX_ADDRESS_LINES = 7


def default_amazon_template_path():
    return AMAZON_TEMPLATE_PATH


def normalize_prn_mode(mode):
    return PRN_MODE_DYNAMIC if mode == PRN_MODE_DYNAMIC else PRN_MODE_TEMPLATE


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


def field_line(label, value):
    return text_fit(f"{label:<{FIELD_LABEL_WIDTH}}: {clean_text(value)}", 62)


def add_field(lines, side, y, label, value, positions):
    field_x = x_from_left_mm(side, positions["prn_field_label_anchor_x_mm"])
    colon_x = x_from_left_mm(side, positions["prn_field_colon_anchor_x_mm"])
    value_x = x_from_left_mm(side, positions["prn_field_value_anchor_x_mm"])
    lines.append(text_cmd(field_x, y, "0", 180, 4, 4, label))
    lines.append(text_cmd(colon_x, y, "0", 180, 4, 4, ":"))
    lines.append(text_cmd(value_x, y, "0", 180, 4, 4, text_fit(value, 42)))


def add_label(lines, row, branch, side):
    payload = build_amazon_label_payload(row, branch)
    coords = BARTENDER_COORDS[side]
    heading_x, heading_y = coords["heading"]
    field_x, field_y = coords["field"]
    barcode_x, barcode_y = coords["barcode"]
    barcode_text_x, barcode_text_y = coords["barcode_text"]
    title_x, title_y = coords["title"]

    lines.append(text_cmd(heading_x, heading_y, "0", 180, 12, 10, payload["heading"]))

    for index, (label, value) in enumerate(payload["field_rows"]):
        y = field_y - index * FIELD_ROW_GAP_DOTS
        lines.append(text_cmd(field_x, y, "ROMAN.TTF", 180, 1, 5, field_line(label, value)))

    lines.append(text_cmd(field_x, CARE_HEADING_Y, "0", 180, 3, 4, payload["care_heading"]))
    for index, line in enumerate(payload["address_lines"][:MAX_ADDRESS_LINES]):
        lines.append(text_cmd(field_x, ADDRESS_START_Y - index * ADDRESS_GAP_DOTS, "0", 180, 3, 4, text_fit(line, 50)))

    lines.append(barcode_cmd(barcode_x, barcode_y, payload["fnsku"]))
    lines.append(text_cmd(barcode_text_x, barcode_text_y, "ROMAN.TTF", 180, 1, 8, payload["fnsku"]))
    lines.append(text_cmd(title_x, title_y, "0", 180, 5, 6, payload["title"]))


def _split_prn_bytes(raw):
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")


def _is_dynamic_template_line(line):
    upper = line.lstrip().upper()
    return upper.startswith(b"TEXT ") or upper.startswith(b"BARCODE ") or upper.startswith(b"PRINT")


def _read_template_static_lines(template_path):
    path = Path(template_path)
    if not path.exists():
        raise RuntimeError(AMAZON_TEMPLATE_MISSING_MESSAGE)

    raw = path.read_bytes()
    if not raw.strip():
        raise RuntimeError(AMAZON_TEMPLATE_MISSING_MESSAGE)

    static_lines = []
    has_bitmap = False
    has_cls = False
    has_codepage = False
    for line in _split_prn_bytes(raw):
        if _is_dynamic_template_line(line):
            continue
        upper = line.lstrip().upper()
        if upper.startswith(b"BITMAP "):
            has_bitmap = True
        elif upper == b"CLS":
            has_cls = True
        elif upper.startswith(b"CODEPAGE"):
            has_codepage = True
        static_lines.append(line)

    if not has_bitmap:
        raise RuntimeError("Amazon BarTender template PRN does not contain a BITMAP block.")
    if not has_cls:
        static_lines.append(b"CLS")
    if not has_codepage:
        static_lines.append(b"CODEPAGE 1252")
    while static_lines and static_lines[-1] == b"":
        static_lines.pop()
    return static_lines


def _encode_dynamic_lines(lines):
    return [line.encode("cp1252", errors="replace") for line in lines]


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


def generate_amazon_prn_from_template(out, rows, branch, template_path=None, progress_callback=None):
    static_lines = _read_template_static_lines(template_path or default_amazon_template_path())
    labels = list(expanded_rows(rows))
    total = len(labels)
    out_lines = []
    done = 0
    for idx in range(0, total, 2):
        out_lines.extend(static_lines)
        dynamic_lines = []
        add_label(dynamic_lines, labels[idx], branch, "left")
        done += 1
        if idx + 1 < total:
            add_label(dynamic_lines, labels[idx + 1], branch, "right")
            done += 1
        out_lines.extend(_encode_dynamic_lines(dynamic_lines))
        out_lines.append(b"PRINT 1,1")
        if progress_callback and (done == total or done % 100 == 0):
            progress_callback(done, total)

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        f.write(b"\r\n".join(out_lines))
        f.write(b"\r\n")
    return total
