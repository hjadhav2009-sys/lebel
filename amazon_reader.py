from pathlib import Path

from amazon_rules import DEFAULT_BRANDS, DEFAULT_CATEGORIES, clean_text, normal_text

try:
    import pandas as pd
except Exception:
    pd = None


CONSIGNMENT_ALIASES = {
    "merchant_sku": ["Merchant SKU", "merchant-sku", "merchant sku", "seller-sku", "seller sku", "SKU"],
    "title": ["Title", "item-name", "item name", "product title"],
    "asin": ["ASIN", "asin1", "product-id", "product id"],
    "fnsku": ["FNSKU", "fn sku"],
    "shipped_qty": ["Shipped", "shipped qty", "quantity shipped", "qty"],
    "condition": ["Condition"],
}

MASTER_ALIASES = {
    "item_name": ["item-name", "item name", "Title", "product title"],
    "item_description": ["item-description", "item description", "description"],
    "seller_sku": ["seller-sku", "seller sku", "Merchant SKU", "SKU"],
    "asin": ["asin1", "ASIN", "asin"],
    "product_id": ["product-id", "product id"],
    "mrp": ["maximum-retail-price", "maximum retail price", "MRP", "mrp", "list price"],
}

NON_OPTION_KEYS = {
    "main heading",
    "brand name",
    "brand",
    "sku no",
    "sku",
    "net quantity",
    "mrp",
    "generic name",
    "address",
    "fsku barcode",
    "fnsku barcode",
    "barcode",
    "title",
    "condition",
    "shipped",
}


def ensure_pandas():
    if pd is None:
        raise RuntimeError("pandas/openpyxl is not installed. Run install_requirements.bat first.")


def norm_col(value):
    return normal_text(value).replace(" ", "_")


def make_unique_columns(values):
    seen = {}
    columns = []
    for i, value in enumerate(values):
        col = clean_text(value) or f"Column {i + 1}"
        base = col
        count = seen.get(base, 0)
        if count:
            col = f"{base}_{count + 1}"
        seen[base] = count + 1
        columns.append(col)
    return columns


def find_col(df, wanted, aliases=None):
    if df is None or df.empty:
        return None
    aliases = aliases or []
    candidates = [wanted] + list(aliases)
    exact = {norm_col(c): c for c in df.columns}
    for candidate in candidates:
        key = norm_col(candidate)
        if key in exact:
            return exact[key]
    for key, original in exact.items():
        for candidate in candidates:
            ckey = norm_col(candidate)
            if ckey and ckey in key:
                return original
    return None


def value_from(row, column, default=""):
    if not column:
        return default
    try:
        return clean_text(row.get(column, default))
    except Exception:
        return default


def mapped_col(df, mapping, group, internal_name):
    configured = mapping.get(group, {}).get(internal_name, "")
    aliases = CONSIGNMENT_ALIASES.get(internal_name, []) if group == "consignment" else MASTER_ALIASES.get(internal_name, [])
    return find_col(df, configured, aliases)


def aliases_with_mapping(group, mapping):
    base = CONSIGNMENT_ALIASES if group == "consignment" else MASTER_ALIASES
    merged = {field: list(values) for field, values in base.items()}
    for field, configured in mapping.get(group, {}).items():
        configured = clean_text(configured)
        if configured:
            merged.setdefault(field, [])
            if configured not in merged[field]:
                merged[field].insert(0, configured)
    return merged


def mapped_value(df, row, mapping, group, internal_name, default=""):
    return value_from(row, mapped_col(df, mapping, group, internal_name), default)


def normalized_sheet_lookup(sheet_names):
    return {normal_text(name): name for name in sheet_names}


def find_sheet(sheet_names, names):
    lookup = normalized_sheet_lookup(sheet_names)
    for name in names:
        key = normal_text(name)
        if key in lookup:
            return lookup[key]
    for original in sheet_names:
        key = normal_text(original)
        for name in names:
            if normal_text(name) in key:
                return original
    return None


def header_row_score(values, aliases_by_field, required_groups):
    row_keys = {norm_col(v) for v in values if clean_text(v)}
    field_hits = {}
    for field, aliases in aliases_by_field.items():
        for alias in aliases:
            alias_key = norm_col(alias)
            if alias_key in row_keys:
                field_hits[field] = True
                break
    for group in required_groups:
        if all(field_hits.get(field) for field in group):
            return len(field_hits)
    return 0


def find_header_row(path, sheet_name, aliases_by_field, required_groups, max_scan_rows=50):
    ensure_pandas()
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, dtype=str, nrows=max_scan_rows).fillna("")
    best_row = None
    best_score = 0
    for idx, row in raw.iterrows():
        score = header_row_score(list(row), aliases_by_field, required_groups)
        if score > best_score:
            best_score = score
            best_row = int(idx)
    if best_row is None:
        return None
    return best_row


def read_table_auto_header(path, sheet_name, aliases_by_field, required_groups, max_scan_rows=50):
    ensure_pandas()
    header_row = find_header_row(path, sheet_name, aliases_by_field, required_groups, max_scan_rows=max_scan_rows)
    if header_row is None:
        return None, None
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, dtype=str).fillna("")
    columns = make_unique_columns(list(raw.iloc[header_row]))
    df = raw.iloc[header_row + 1:].copy()
    df.columns = columns
    df = df.reset_index(drop=True).fillna("")
    return df, header_row


def sheet_order(sheet_names, preferred_names):
    preferred = []
    for name in preferred_names:
        found = find_sheet(sheet_names, [name])
        if found and found not in preferred:
            preferred.append(found)
    return preferred + [name for name in sheet_names if name not in preferred]


def is_amazon_columns(columns):
    keys = {norm_col(c) for c in columns}
    has_merchant = any(norm_col(a) in keys for a in CONSIGNMENT_ALIASES["merchant_sku"])
    has_fnsku = any(norm_col(a) in keys for a in CONSIGNMENT_ALIASES["fnsku"])
    has_shipped = any(norm_col(a) in keys for a in CONSIGNMENT_ALIASES["shipped_qty"])
    has_asin = any(norm_col(a) in keys for a in CONSIGNMENT_ALIASES["asin"])
    return (has_merchant and has_fnsku and has_shipped) or (has_asin and has_fnsku)


def detect_amazon_workbook(path, mapping=None):
    ensure_pandas()
    mapping = mapping or {"consignment": {}}
    consignment_aliases = aliases_with_mapping("consignment", mapping)
    xl = pd.ExcelFile(path)
    if find_sheet(xl.sheet_names, ["given by amazon for label"]):
        return True
    for sheet_name in xl.sheet_names:
        header = find_header_row(
            path,
            sheet_name,
            consignment_aliases,
            [("merchant_sku", "fnsku", "shipped_qty"), ("asin", "fnsku")],
        )
        if header is not None:
            return True
    return False


def detect_master_listing_workbook(path, mapping=None):
    ensure_pandas()
    mapping = mapping or {"master": {}}
    master_aliases = aliases_with_mapping("master", mapping)
    xl = pd.ExcelFile(path)
    for sheet_name in xl.sheet_names:
        header = find_header_row(
            path,
            sheet_name,
            master_aliases,
            [("asin", "mrp"), ("product_id", "mrp")],
        )
        if header is not None:
            return True
    return False


def filter_consignment_rows(df, mapping):
    important = [
        mapped_col(df, mapping, "consignment", "merchant_sku"),
        mapped_col(df, mapping, "consignment", "title"),
        mapped_col(df, mapping, "consignment", "asin"),
        mapped_col(df, mapping, "consignment", "fnsku"),
        mapped_col(df, mapping, "consignment", "shipped_qty"),
    ]
    important = [c for c in important if c]
    if not important:
        return df
    keep = []
    for _, row in df.iterrows():
        keep.append(any(clean_text(row.get(c, "")) for c in important))
    return df.loc[keep].reset_index(drop=True).fillna("")


def filter_master_rows(df, mapping):
    important = [
        mapped_col(df, mapping, "master", "asin"),
        mapped_col(df, mapping, "master", "product_id"),
        mapped_col(df, mapping, "master", "mrp"),
        mapped_col(df, mapping, "master", "item_name"),
        mapped_col(df, mapping, "master", "seller_sku"),
    ]
    important = [c for c in important if c]
    if not important:
        return df
    keep = []
    for _, row in df.iterrows():
        keep.append(any(clean_text(row.get(c, "")) for c in important))
    return df.loc[keep].reset_index(drop=True).fillna("")


def extract_need_sheet_options(path, sheet_name):
    ensure_pandas()
    categories = set()
    brands = set()
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, dtype=str).fillna("")

    category_keys = {normal_text(c): c for c in DEFAULT_CATEGORIES}
    brand_keys = {normal_text(b): b for b in DEFAULT_BRANDS}
    rows, cols = raw.shape

    def option_candidate(candidate, kind):
        candidate = clean_text(candidate)
        key = normal_text(candidate)
        if not candidate or len(candidate) > 60:
            return False
        if ":" in candidate or key in NON_OPTION_KEYS:
            return False
        if "field" in key or "label" in key:
            return False
        if kind == "brand" and key in category_keys:
            return False
        if kind == "category" and key in brand_keys:
            return False
        return True

    for r in range(rows):
        for c in range(cols):
            value = clean_text(raw.iat[r, c])
            key = normal_text(value)
            if key in category_keys:
                categories.add(category_keys[key])
            if key in brand_keys:
                brands.add(brand_keys[key])

            if "brand" in key:
                for rr in range(r, min(rows, r + 20)):
                    candidate = clean_text(raw.iat[rr, c])
                    if option_candidate(candidate, "brand") and "brand" not in normal_text(candidate):
                        brands.add(candidate)
                for cc in range(c + 1, min(cols, c + 8)):
                    candidate = clean_text(raw.iat[r, cc])
                    if option_candidate(candidate, "brand"):
                        brands.add(candidate)

            if "main heading" in key or "category" in key:
                for rr in range(r, min(rows, r + 20)):
                    candidate = clean_text(raw.iat[rr, c])
                    if option_candidate(candidate, "category") and "heading" not in normal_text(candidate) and "category" not in normal_text(candidate):
                        categories.add(candidate)
                for cc in range(c + 1, min(cols, c + 8)):
                    candidate = clean_text(raw.iat[r, cc])
                    if option_candidate(candidate, "category"):
                        categories.add(candidate)

    return sorted(categories), sorted(brands)


def load_master_listing_file(path, mapping):
    ensure_pandas()
    path = str(path)
    suffix = Path(path).suffix.lower()
    if suffix not in (".xlsx", ".xls"):
        raise RuntimeError("Weekly master listing must be an Excel workbook (.xlsx/.xls).")

    xl = pd.ExcelFile(path)
    master_aliases = aliases_with_mapping("master", mapping)
    master_df = None
    master_sheet = ""
    master_header = None
    for sheet_name in sheet_order(xl.sheet_names, ["all lsiting", "all listing", "listing", "Sheet1"]):
        candidate_df, candidate_header = read_table_auto_header(
            path,
            sheet_name,
            master_aliases,
            [("asin", "mrp"), ("product_id", "mrp")],
            max_scan_rows=50,
        )
        if candidate_df is not None:
            master_df = filter_master_rows(candidate_df, mapping)
            master_sheet = sheet_name
            master_header = candidate_header
            break
    if master_df is None:
        raise RuntimeError("Could not find master listing header. Need ASIN/product-id and maximum-retail-price/MRP columns.")

    mrp_col = mapped_col(master_df, mapping, "master", "mrp") or ""
    return {
        "path": path,
        "sheet_names": xl.sheet_names,
        "master_sheet": master_sheet,
        "master_header_row": master_header,
        "master_df": master_df,
        "mrp_col": mrp_col,
        "detected_columns": {"master": list(master_df.columns)},
    }


def load_consignment_file(path, mapping):
    ensure_pandas()
    path = str(path)
    suffix = Path(path).suffix.lower()
    if suffix not in (".xlsx", ".xls"):
        raise RuntimeError("Amazon consignment file must be an Excel workbook (.xlsx/.xls).")

    xl = pd.ExcelFile(path)
    consignment_aliases = aliases_with_mapping("consignment", mapping)
    consignment_df = None
    consignment_sheet = ""
    consignment_header = None
    for sheet_name in sheet_order(xl.sheet_names, ["given by amazon for label"]):
        candidate_df, candidate_header = read_table_auto_header(
            path,
            sheet_name,
            consignment_aliases,
            [("merchant_sku", "fnsku", "shipped_qty"), ("asin", "fnsku")],
            max_scan_rows=50,
        )
        if candidate_df is not None:
            consignment_df = filter_consignment_rows(candidate_df, mapping)
            consignment_sheet = sheet_name
            consignment_header = candidate_header
            break
    if consignment_df is None:
        raise RuntimeError("Could not find Amazon label table header. It should contain Merchant SKU/FNSKU/Shipped or ASIN/FNSKU.")

    need_sheet = find_sheet(xl.sheet_names, ["need in label", "need in label "])
    categories, brands = [], []
    if need_sheet:
        categories, brands = extract_need_sheet_options(path, need_sheet)

    return {
        "path": path,
        "sheet_names": xl.sheet_names,
        "consignment_sheet": consignment_sheet,
        "consignment_header_row": consignment_header,
        "consignment_df": consignment_df,
        "need_sheet": need_sheet or "",
        "sheet_categories": categories,
        "sheet_brands": brands,
        "detected_columns": {"consignment": list(consignment_df.columns)},
    }


def load_amazon_workbook(path, mapping):
    ensure_pandas()
    path = str(path)
    suffix = Path(path).suffix.lower()
    if suffix not in (".xlsx", ".xls"):
        raise RuntimeError("Amazon upload must be an Excel workbook (.xlsx/.xls).")

    consignment = load_consignment_file(path, mapping)
    try:
        master = load_master_listing_file(path, mapping)
    except Exception:
        master = {
            "master_sheet": "",
            "master_header_row": None,
            "master_df": pd.DataFrame(),
            "mrp_col": "",
            "detected_columns": {"master": []},
        }

    return {
        "path": path,
        "sheet_names": consignment.get("sheet_names", []),
        "consignment_sheet": consignment.get("consignment_sheet", ""),
        "consignment_header_row": consignment.get("consignment_header_row"),
        "consignment_df": consignment.get("consignment_df"),
        "master_sheet": master.get("master_sheet", ""),
        "master_header_row": master.get("master_header_row"),
        "master_df": master.get("master_df"),
        "need_sheet": consignment.get("need_sheet", ""),
        "sheet_categories": consignment.get("sheet_categories", []),
        "sheet_brands": consignment.get("sheet_brands", []),
        "mrp_col": master.get("mrp_col", ""),
        "detected_columns": {
            "consignment": consignment.get("detected_columns", {}).get("consignment", []),
            "master": master.get("detected_columns", {}).get("master", []),
        },
    }
