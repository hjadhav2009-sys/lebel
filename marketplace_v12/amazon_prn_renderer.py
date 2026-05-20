import sys
from pathlib import Path
import re

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
    from . import runtime_paths
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
    import runtime_paths


BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
AMAZON_TEMPLATE_MISSING_MESSAGE = (
    "Amazon BarTender template PRN missing. Dynamic TSPL No Bitmap does not require "
    "a template; use template mode only for advanced debugging."
)

PRN_MODE_TEMPLATE = "template_barcode_bitmap"
PRN_MODE_DYNAMIC = "dynamic_tspl"
TEMPLATE_SUBTYPE_BLANK = "blank_template"
TEMPLATE_SUBTYPE_CAPTION = "caption_template"

PRN_OPTION_DYNAMIC = "Dynamic TSPL No Bitmap"
PRN_OPTION_TEMPLATE_BLANK = "Template Bitmap - Blank"
PRN_OPTION_TEMPLATE_CAPTIONS = "Template Bitmap - Captions"
PRN_MODE_VALUES = [PRN_OPTION_DYNAMIC, PRN_OPTION_TEMPLATE_BLANK, PRN_OPTION_TEMPLATE_CAPTIONS]

TEMPLATE_LAYOUT_DYNAMIC = "Dynamic TSPL No Bitmap"
TEMPLATE_LAYOUT_2UP_BLANK = "2UP Blank Template 101.5x50"
TEMPLATE_LAYOUT_2UP_CAPTION = "2UP Caption Template 101.5x50"
TEMPLATE_LAYOUT_4UP_CAPTION = "4UP Caption Template 101.6x101.6"
TEMPLATE_LAYOUT_VALUES = [
    TEMPLATE_LAYOUT_2UP_BLANK,
    TEMPLATE_LAYOUT_2UP_CAPTION,
    TEMPLATE_LAYOUT_4UP_CAPTION,
    TEMPLATE_LAYOUT_DYNAMIC,
]

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

BARTENDER_2UP_COORDS = {
    "left": {
        "heading": (278, 385),
        "field": (355, 354),
        "value": (231, 354),
        "care": (355, 268),
        "address": (355, 246),
        "barcode": (361, 122),
        "barcode_text": (300, 76),
        "title": (374, 48),
    },
    "right": {
        "heading": (689, 385),
        "field": (766, 354),
        "value": (642, 354),
        "care": (766, 268),
        "address": (766, 246),
        "barcode": (772, 122),
        "barcode_text": (711, 76),
        "title": (785, 48),
    },
}
BARTENDER_COORDS = BARTENDER_2UP_COORDS
BARTENDER_4UP_COORDS = {
    "top_left": {
        "heading": (278, 797),
        "field": (354, 766),
        "value": (230, 766),
        "care": (354, 676),
        "address": (354, 656),
        "barcode": (360, 534),
        "barcode_text": (276, 488),
        "title": (374, 460),
    },
    "top_right": {
        "heading": (689, 797),
        "field": (775, 766),
        "value": (651, 766),
        "care": (775, 676),
        "address": (775, 656),
        "barcode": (781, 534),
        "barcode_text": (697, 488),
        "title": (785, 460),
    },
    "bottom_left": {
        "heading": (278, 385),
        "field": (354, 354),
        "value": (230, 354),
        "care": (354, 264),
        "address": (354, 244),
        "barcode": (360, 122),
        "barcode_text": (276, 76),
        "title": (374, 48),
    },
    "bottom_right": {
        "heading": (689, 385),
        "field": (775, 354),
        "value": (651, 354),
        "care": (775, 264),
        "address": (775, 244),
        "barcode": (781, 122),
        "barcode_text": (697, 76),
        "title": (785, 48),
    },
}
FIELD_ROW_GAP_DOTS = 16
ADDRESS_GAP_DOTS = 15
FIELD_LABEL_WIDTH = 16
MAX_ADDRESS_LINES = 7
CAPTION_TEXT_MARKERS = [
    b"BRAND",
    b"SKU NO",
    b"NET QUANTITY",
    b"MRP",
    b"GENERIC NAME",
]
PLACEHOLDER_MARKERS = [b"X0000000000"]


def get_resource_path(relative_path):
    return runtime_paths.get_resource_path(relative_path)


def ensure_default_resources_installed():
    return runtime_paths.ensure_default_resources_installed()


def default_amazon_template_path():
    return runtime_paths.amazon_template_path()


def normalize_prn_mode(mode):
    text = clean_text(mode)
    if text in (PRN_MODE_DYNAMIC, PRN_OPTION_DYNAMIC, TEMPLATE_LAYOUT_DYNAMIC):
        return PRN_MODE_DYNAMIC
    return PRN_MODE_TEMPLATE


def normalize_template_subtype(value):
    text = clean_text(value)
    if text in (TEMPLATE_SUBTYPE_BLANK, PRN_OPTION_TEMPLATE_BLANK, TEMPLATE_LAYOUT_2UP_BLANK):
        return TEMPLATE_SUBTYPE_BLANK
    return TEMPLATE_SUBTYPE_CAPTION


def prn_option_for(mode, subtype):
    if normalize_prn_mode(mode) == PRN_MODE_DYNAMIC:
        return PRN_OPTION_DYNAMIC
    if normalize_template_subtype(subtype) == TEMPLATE_SUBTYPE_BLANK:
        return PRN_OPTION_TEMPLATE_BLANK
    return PRN_OPTION_TEMPLATE_CAPTIONS


def mode_from_prn_option(option):
    if option == PRN_OPTION_DYNAMIC:
        return PRN_MODE_DYNAMIC, TEMPLATE_SUBTYPE_BLANK
    if option == PRN_OPTION_TEMPLATE_BLANK:
        return PRN_MODE_TEMPLATE, TEMPLATE_SUBTYPE_BLANK
    return PRN_MODE_TEMPLATE, TEMPLATE_SUBTYPE_CAPTION


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


def _coords_for_slot(slot):
    if slot in BARTENDER_4UP_COORDS:
        return BARTENDER_4UP_COORDS[slot]
    return BARTENDER_2UP_COORDS["right" if slot == "right" else "left"]


def _layout_slots(template_layout):
    if template_layout == TEMPLATE_LAYOUT_4UP_CAPTION:
        return ["top_left", "top_right", "bottom_left", "bottom_right"]
    return ["left", "right"]


def add_label(lines, row, branch, slot, caption_values_only=False):
    payload = build_amazon_label_payload(row, branch)
    coords = _coords_for_slot(slot)
    heading_x, heading_y = coords["heading"]
    field_x, field_y = coords["field"]
    value_x, value_y = coords["value"]
    care_x, care_y = coords["care"]
    address_x, address_y = coords["address"]
    barcode_x, barcode_y = coords["barcode"]
    barcode_text_x, barcode_text_y = coords["barcode_text"]
    title_x, title_y = coords["title"]

    lines.append(text_cmd(heading_x, heading_y, "0", 180, 12, 10, payload["heading"]))

    for index, (label, value) in enumerate(payload["field_rows"]):
        y = field_y - index * FIELD_ROW_GAP_DOTS
        if caption_values_only:
            lines.append(text_cmd(value_x, value_y - index * FIELD_ROW_GAP_DOTS, "ROMAN.TTF", 180, 1, 5, text_fit(value, 46)))
        else:
            lines.append(text_cmd(field_x, y, "ROMAN.TTF", 180, 1, 5, field_line(label, value)))

    lines.append(text_cmd(care_x, care_y, "0", 180, 3, 4, payload["care_heading"]))
    for index, line in enumerate(payload["address_lines"][:MAX_ADDRESS_LINES]):
        lines.append(text_cmd(address_x, address_y - index * ADDRESS_GAP_DOTS, "ROMAN.TTF", 180, 1, 5, text_fit(line, 54)))

    lines.append(barcode_cmd(barcode_x, barcode_y, payload["fnsku"]))
    lines.append(text_cmd(barcode_text_x, barcode_text_y, "ROMAN.TTF", 180, 1, 8, payload["fnsku"]))
    lines.append(text_cmd(title_x, title_y, "0", 180, 5, 6, payload["title"]))


def _split_prn_bytes(raw):
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")


def _is_dynamic_template_line(line):
    upper = line.lstrip().upper()
    return upper.startswith(b"TEXT ") or upper.startswith(b"BARCODE ") or upper.startswith(b"PRINT")


def _line_text_bytes(line):
    return line.upper().replace(b"\x00", b" ")


def _is_caption_text_line(line):
    upper = _line_text_bytes(line)
    return upper.lstrip().startswith(b"TEXT ") and any(marker in upper for marker in CAPTION_TEXT_MARKERS)


def _is_placeholder_line(line):
    upper = _line_text_bytes(line)
    return any(marker in upper for marker in PLACEHOLDER_MARKERS)


def _parse_size_line(line):
    try:
        text = line.decode("cp1252", errors="ignore")
    except Exception:
        text = str(line)
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    if len(nums) >= 2:
        try:
            return float(nums[0]), float(nums[1])
        except Exception:
            return None, None
    return None, None


def _size_is_close(value, expected):
    return value is not None and abs(float(value) - float(expected)) <= 0.4


def validate_amazon_template(template_path=None):
    path = Path(template_path or default_amazon_template_path())
    result = {
        "path": path,
        "exists": path.exists(),
        "size_line": "",
        "gap_line": "",
        "width_mm": None,
        "height_mm": None,
        "has_bitmap": False,
        "has_captions": False,
        "has_placeholder_barcode": False,
        "is_expected_size": False,
        "suggested_layout": TEMPLATE_LAYOUT_DYNAMIC,
        "warnings": [],
    }
    if not path.exists():
        result["warnings"].append(AMAZON_TEMPLATE_MISSING_MESSAGE)
        return result
    raw = path.read_bytes()
    for line in _split_prn_bytes(raw):
        upper = line.lstrip().upper()
        if upper.startswith(b"SIZE "):
            result["size_line"] = line.decode("cp1252", errors="ignore")
            result["width_mm"], result["height_mm"] = _parse_size_line(line)
        elif upper.startswith(b"GAP "):
            result["gap_line"] = line.decode("cp1252", errors="ignore")
        elif upper.startswith(b"BITMAP "):
            result["has_bitmap"] = True
        elif upper.startswith(b"TEXT ") and _is_caption_text_line(line):
            result["has_captions"] = True
        elif upper.startswith(b"BARCODE ") and _is_placeholder_line(line):
            result["has_placeholder_barcode"] = True

    width = result["width_mm"]
    height = result["height_mm"]
    is_2up = _size_is_close(width, 101.5) and _size_is_close(height, 50.0)
    is_4up = _size_is_close(width, 101.6) and _size_is_close(height, 101.6)
    result["is_expected_size"] = is_2up or is_4up
    if is_4up:
        result["suggested_layout"] = TEMPLATE_LAYOUT_4UP_CAPTION if result["has_captions"] else TEMPLATE_LAYOUT_2UP_BLANK
    elif is_2up:
        result["suggested_layout"] = TEMPLATE_LAYOUT_2UP_CAPTION if result["has_captions"] else TEMPLATE_LAYOUT_2UP_BLANK

    if not result["has_bitmap"]:
        result["warnings"].append("Amazon template PRN does not contain a BITMAP block.")
    if not result["is_expected_size"]:
        result["warnings"].append(
            f"Amazon template SIZE is not expected: {result['size_line'] or 'missing SIZE line'}"
        )
    if result["has_bitmap"]:
        result["warnings"].append(
            "Template bitmap may contain fixed address. Print one blank template test to confirm no old address is burned into bitmap."
        )
    return result


def template_validation_is_usable(validation):
    return bool(validation.get("exists") and validation.get("has_bitmap") and validation.get("is_expected_size"))


def _read_template_static_lines(template_path, keep_caption_text=False):
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
        if _is_placeholder_line(line):
            continue
        if _is_dynamic_template_line(line) and not (keep_caption_text and _is_caption_text_line(line)):
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
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="cp1252", errors="replace", newline="\r\n") as f:
        f.write("\n".join(out_lines))
        f.write("\n")
    return total


def generate_amazon_prn_from_template(
    out,
    rows,
    branch,
    template_path=None,
    progress_callback=None,
    template_layout=TEMPLATE_LAYOUT_2UP_BLANK,
    template_subtype=TEMPLATE_SUBTYPE_BLANK,
):
    validation = validate_amazon_template(template_path or default_amazon_template_path())
    if not template_validation_is_usable(validation):
        raise RuntimeError("\n".join(validation.get("warnings") or [AMAZON_TEMPLATE_MISSING_MESSAGE]))
    keep_caption_text = normalize_template_subtype(template_subtype) == TEMPLATE_SUBTYPE_CAPTION
    static_lines = _read_template_static_lines(template_path or default_amazon_template_path(), keep_caption_text=keep_caption_text)
    labels = list(expanded_rows(rows))
    total = len(labels)
    out_lines = []
    done = 0
    slots = _layout_slots(template_layout)
    labels_per_page = len(slots)
    caption_values_only = normalize_template_subtype(template_subtype) == TEMPLATE_SUBTYPE_CAPTION
    for idx in range(0, total, labels_per_page):
        out_lines.extend(static_lines)
        dynamic_lines = []
        for offset, slot in enumerate(slots):
            label_index = idx + offset
            if label_index >= total:
                break
            add_label(dynamic_lines, labels[label_index], branch, slot, caption_values_only=caption_values_only)
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
