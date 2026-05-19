import csv
import re

from amazon_reader import mapped_col, mapped_value
from amazon_rules import clean_text, detect_brand, detect_category, row_identity


def parse_positive_int(value):
    text = clean_text(value)
    if not text:
        return 0
    try:
        number = int(float(text))
        return number if number > 0 else 0
    except Exception:
        return 0


def normalize_mrp(value):
    text = clean_text(value)
    if not text:
        return ""
    text = text.replace(",", "")
    text = re.sub(r"(?i)(rs\.?|inr|mrp|inclusive|of|all|taxes)", " ", text)
    text = re.sub(r"[^0-9.]+", " ", text)
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return ""
    try:
        return f"{float(match.group(0)):.2f}"
    except Exception:
        return ""


def format_mrp(value):
    mrp = normalize_mrp(value)
    return f"MRP Rs.{mrp} Inclusive of all taxes" if mrp else ""


def _master_row_text(row, item_col, desc_col):
    pieces = []
    if item_col:
        pieces.append(clean_text(row.get(item_col, "")))
    if desc_col:
        pieces.append(clean_text(row.get(desc_col, "")))
    return " ".join([p for p in pieces if p])


def build_master_index(master_df, mapping):
    index = {}
    if master_df is None or master_df.empty:
        return index

    asin_col = mapped_col(master_df, mapping, "master", "asin")
    product_col = mapped_col(master_df, mapping, "master", "product_id")
    mrp_col = mapped_col(master_df, mapping, "master", "mrp")
    item_col = mapped_col(master_df, mapping, "master", "item_name")
    desc_col = mapped_col(master_df, mapping, "master", "item_description")

    for _, row in master_df.iterrows():
        mrp = normalize_mrp(row.get(mrp_col, "")) if mrp_col else ""
        text = _master_row_text(row, item_col, desc_col)
        payload = {"row": row, "mrp": mrp, "text": text}
        for col in (asin_col, product_col):
            if not col:
                continue
            key = clean_text(row.get(col, ""))
            if key:
                index.setdefault(key.lower(), payload)
    return index


def resolve_amazon_rows(workbook, mapping, category_rules, brand_rules, manual_mrp=None, qty_overrides=None):
    manual_mrp = manual_mrp or {}
    qty_overrides = qty_overrides or {}
    consignment_df = workbook["consignment_df"]
    master_index = build_master_index(workbook.get("master_df"), mapping)
    rows = []

    for source_index, source_row in consignment_df.iterrows():
        row = {
            "source_index": int(source_index),
            "merchant_sku": mapped_value(consignment_df, source_row, mapping, "consignment", "merchant_sku"),
            "title": mapped_value(consignment_df, source_row, mapping, "consignment", "title"),
            "asin": mapped_value(consignment_df, source_row, mapping, "consignment", "asin"),
            "fnsku": mapped_value(consignment_df, source_row, mapping, "consignment", "fnsku"),
            "condition": mapped_value(consignment_df, source_row, mapping, "consignment", "condition"),
            "shipped_qty_raw": mapped_value(consignment_df, source_row, mapping, "consignment", "shipped_qty"),
        }
        key = row_identity(row)
        shipped_qty = parse_positive_int(row["shipped_qty_raw"])
        row["print_qty"] = parse_positive_int(qty_overrides.get(key, shipped_qty)) or shipped_qty

        master_payload = master_index.get(clean_text(row["asin"]).lower())
        master_text = ""
        master_mrp = ""
        if master_payload:
            master_text = master_payload.get("text", "")
            master_mrp = master_payload.get("mrp", "")

        manual_value = manual_mrp.get(key) or manual_mrp.get(clean_text(row["asin"]).lower()) or ""
        row["mrp"] = normalize_mrp(manual_value) or master_mrp
        row["mrp_source"] = "manual" if normalize_mrp(manual_value) else ("master" if master_mrp else "")
        row["main_heading"] = detect_category(row, master_text, category_rules)
        row["brand"] = detect_brand(row, brand_rules)
        row["generic_name"] = row["main_heading"]
        row["row_key"] = key
        row["status"] = "PASS"
        row["errors"] = []
        rows.append(row)
    return rows


def branch_errors(branch):
    if not branch:
        return ["Branch/address settings missing"]
    missing = []
    if not clean_text(branch.get("marketed_by", "")):
        missing.append("Branch company/marketed by missing")
    if not clean_text(branch.get("address", "")):
        missing.append("Branch address missing")
    if not clean_text(branch.get("email", "")):
        missing.append("Branch email missing")
    if not clean_text(branch.get("phone", "")):
        missing.append("Branch contact missing")
    return missing


def validate_amazon_rows(rows, branch):
    common_branch_errors = branch_errors(branch)
    validated = []
    for row in rows:
        errors = []
        if not clean_text(row.get("merchant_sku", "")):
            errors.append("Missing SKU")
        if not clean_text(row.get("fnsku", "")):
            errors.append("Missing FNSKU")
        if not clean_text(row.get("main_heading", "")):
            errors.append("Missing Main Heading")
        if not clean_text(row.get("brand", "")):
            errors.append("Missing Brand Name")
        if not normalize_mrp(row.get("mrp", "")):
            errors.append("Missing MRP")
        if parse_positive_int(row.get("print_qty", "")) <= 0:
            errors.append("Invalid or zero quantity")
        errors.extend(common_branch_errors)
        row["errors"] = errors
        row["status"] = "PASS" if not errors else "FAIL"
        validated.append(row)
    return validated


def has_blocking_errors(rows):
    return any(row.get("errors") for row in rows)


def report_rows(rows):
    report = []
    for row in rows:
        report.append(
            {
                "Status": row.get("status", ""),
                "SKU": row.get("merchant_sku", ""),
                "ASIN": row.get("asin", ""),
                "FNSKU": row.get("fnsku", ""),
                "Title": row.get("title", ""),
                "Main Heading": row.get("main_heading", ""),
                "Brand": row.get("brand", ""),
                "MRP": row.get("mrp", ""),
                "Print Qty": row.get("print_qty", ""),
                "Error message": "; ".join(row.get("errors", [])),
            }
        )
    return report


def write_report_csv(path, rows):
    fields = ["Status", "SKU", "ASIN", "FNSKU", "Title", "Main Heading", "Brand", "MRP", "Print Qty", "Error message"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in report_rows(rows):
            writer.writerow(row)
