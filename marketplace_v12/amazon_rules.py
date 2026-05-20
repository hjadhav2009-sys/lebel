import json
import re
import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CATEGORY_RULES_FILE = DATA_DIR / "amazon_category_rules.json"
BRAND_RULES_FILE = DATA_DIR / "amazon_brand_rules.json"
MAPPING_SETTINGS_FILE = DATA_DIR / "amazon_mapping_settings.json"


DEFAULT_CATEGORIES = [
    "Pendant Necklace",
    "Bracelet",
    "Keychain",
    "Ring",
    "Earring",
    "Brooch",
    "Car Hanger",
    "Dashbord",
]

DEFAULT_CATEGORY_KEYWORDS = {
    "Pendant Necklace": ["pendant", "necklace", "locket", "chain"],
    "Bracelet": ["bracelet", "bangle", "kada", "wristband"],
    "Keychain": ["keychain", "key chain", "keyring", "key ring"],
    "Ring": ["ring"],
    "Earring": ["earring", "ear stud", "studs", "hoop"],
    "Brooch": ["brooch"],
    "Car Hanger": ["car hanger", "car hanging", "rear view", "rearview", "ornament", "dream catcher"],
    "Dashbord": ["dashboard", "dashbord"],
}

DEFAULT_BRANDS = ["M Men Style", "Tunglaze", "Sullery"]

DEFAULT_MAPPING_SETTINGS = {
    "selected_branch": "",
    "last_master_path": "",
    "pdf_layout": "BarTender 2UP 101.5x50",
    "prn_mode": "template_barcode_bitmap",
    "template_subtype": "caption_template",
    "template_layout": "4UP Caption Template 101.6x101.6",
    "consignment": {
        "merchant_sku": "Merchant SKU",
        "title": "Title",
        "asin": "ASIN",
        "fnsku": "FNSKU",
        "shipped_qty": "Shipped",
        "condition": "Condition",
    },
    "master": {
        "item_name": "item-name",
        "item_description": "item-description",
        "seller_sku": "seller-sku",
        "asin": "asin1",
        "product_id": "product-id",
        "mrp": "maximum-retail-price",
    },
}


def clean_text(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def normal_text(value):
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _load_json(path, default):
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return json.loads(json.dumps(default))


def _write_json(path, data):
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_category_rules():
    data = _load_json(
        CATEGORY_RULES_FILE,
        {
            "categories": DEFAULT_CATEGORIES,
            "keyword_rules": DEFAULT_CATEGORY_KEYWORDS,
            "manual_rules": {},
        },
    )
    changed = False
    categories = data.setdefault("categories", [])
    for category in DEFAULT_CATEGORIES:
        if category not in categories:
            categories.append(category)
            changed = True
    keyword_rules = data.setdefault("keyword_rules", {})
    for category, keywords in DEFAULT_CATEGORY_KEYWORDS.items():
        existing = keyword_rules.setdefault(category, [])
        for keyword in keywords:
            if keyword not in existing:
                existing.append(keyword)
                changed = True
    data.setdefault("manual_rules", {})
    if changed or not CATEGORY_RULES_FILE.exists():
        save_category_rules(data)
    return data


def save_category_rules(data):
    clean = {
        "categories": unique_list(data.get("categories", DEFAULT_CATEGORIES)),
        "keyword_rules": {},
        "manual_rules": data.get("manual_rules", {}),
    }
    for category in clean["categories"]:
        raw_keywords = data.get("keyword_rules", {}).get(category, [])
        if isinstance(raw_keywords, str):
            raw_keywords = split_keywords(raw_keywords)
        clean["keyword_rules"][category] = unique_list([clean_text(k) for k in raw_keywords if clean_text(k)])
    _write_json(CATEGORY_RULES_FILE, clean)


def load_brand_rules():
    data = _load_json(BRAND_RULES_FILE, {"brands": DEFAULT_BRANDS, "manual_rules": {}})
    changed = False
    brands = data.setdefault("brands", [])
    for brand in DEFAULT_BRANDS:
        if brand not in brands:
            brands.append(brand)
            changed = True
    data.setdefault("manual_rules", {})
    if changed or not BRAND_RULES_FILE.exists():
        save_brand_rules(data)
    return data


def save_brand_rules(data):
    clean = {
        "brands": unique_list([clean_text(b) for b in data.get("brands", DEFAULT_BRANDS) if clean_text(b)]),
        "manual_rules": data.get("manual_rules", {}),
    }
    _write_json(BRAND_RULES_FILE, clean)


def load_mapping_settings():
    data = _load_json(MAPPING_SETTINGS_FILE, DEFAULT_MAPPING_SETTINGS)
    changed = False
    for group in ("consignment", "master"):
        target = data.setdefault(group, {})
        for key, value in DEFAULT_MAPPING_SETTINGS[group].items():
            if key not in target:
                target[key] = value
                changed = True
    if "selected_branch" not in data:
        data["selected_branch"] = ""
        changed = True
    if "last_master_path" not in data:
        data["last_master_path"] = ""
        changed = True
    if "pdf_layout" not in data:
        data["pdf_layout"] = DEFAULT_MAPPING_SETTINGS["pdf_layout"]
        changed = True
    if "prn_mode" not in data:
        data["prn_mode"] = DEFAULT_MAPPING_SETTINGS["prn_mode"]
        changed = True
    if "template_layout" not in data:
        data["template_layout"] = DEFAULT_MAPPING_SETTINGS["template_layout"]
        changed = True
    if "template_subtype" not in data:
        data["template_subtype"] = DEFAULT_MAPPING_SETTINGS["template_subtype"]
        changed = True
    if changed or not MAPPING_SETTINGS_FILE.exists():
        save_mapping_settings(data)
    return data


def save_mapping_settings(data):
    clean = {
        "selected_branch": clean_text(data.get("selected_branch", "")),
        "last_master_path": clean_text(data.get("last_master_path", "")),
        "pdf_layout": clean_text(data.get("pdf_layout", DEFAULT_MAPPING_SETTINGS["pdf_layout"])) or DEFAULT_MAPPING_SETTINGS["pdf_layout"],
        "prn_mode": clean_text(data.get("prn_mode", DEFAULT_MAPPING_SETTINGS["prn_mode"])) or DEFAULT_MAPPING_SETTINGS["prn_mode"],
        "template_subtype": clean_text(data.get("template_subtype", DEFAULT_MAPPING_SETTINGS["template_subtype"])) or DEFAULT_MAPPING_SETTINGS["template_subtype"],
        "template_layout": clean_text(data.get("template_layout", DEFAULT_MAPPING_SETTINGS["template_layout"])) or DEFAULT_MAPPING_SETTINGS["template_layout"],
        "consignment": {},
        "master": {},
    }
    for group in ("consignment", "master"):
        for key, value in DEFAULT_MAPPING_SETTINGS[group].items():
            clean[group][key] = clean_text(data.get(group, {}).get(key, value)) or value
    _write_json(MAPPING_SETTINGS_FILE, clean)


def unique_list(values):
    seen = set()
    out = []
    for value in values:
        text = clean_text(value)
        if not text:
            continue
        key = normal_text(text)
        if key and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def split_keywords(text):
    raw = str(text).replace("\n", ",").split(",")
    return [part.strip() for part in raw if part.strip()]


def merge_sheet_options(categories=None, brands=None):
    changed = False
    if categories:
        category_rules = load_category_rules()
        for category in categories:
            category = clean_text(category)
            if category and category not in category_rules["categories"]:
                category_rules["categories"].append(category)
                category_rules.setdefault("keyword_rules", {}).setdefault(category, [])
                changed = True
        if changed:
            save_category_rules(category_rules)

    changed = False
    if brands:
        brand_rules = load_brand_rules()
        for brand in brands:
            brand = clean_text(brand)
            if brand and normal_text(brand) not in {normal_text(b) for b in brand_rules["brands"]}:
                brand_rules["brands"].append(brand)
                changed = True
        if changed:
            save_brand_rules(brand_rules)


def row_rule_keys(row):
    keys = []
    for field in ("merchant_sku", "asin", "fnsku"):
        value = clean_text(row.get(field, ""))
        if value:
            keys.append(f"{field}:{normal_text(value)}")
    title = normal_text(row.get("title", ""))
    if title:
        keys.append(f"title:{title[:160]}")
    return keys


def row_identity(row):
    parts = [
        clean_text(row.get("source_index", "")),
        clean_text(row.get("merchant_sku", "")),
        clean_text(row.get("asin", "")),
        clean_text(row.get("fnsku", "")),
    ]
    return "|".join(parts)


def _manual_match(row, manual_rules):
    for key in row_rule_keys(row):
        value = manual_rules.get(key, "")
        if value:
            return clean_text(value)
    return ""


def _keyword_score(text, keyword):
    keyword = normal_text(keyword)
    if not text or not keyword:
        return 0
    if " " in keyword:
        if keyword in text:
            return 20 + len(keyword)
        return 0
    if re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text):
        return 10 + len(keyword)
    return 0


def detect_category(row, master_text, category_rules=None):
    category_rules = category_rules or load_category_rules()
    manual = _manual_match(row, category_rules.get("manual_rules", {}))
    if manual:
        return manual

    search_blocks = [row.get("title", ""), master_text or ""]
    best_category = ""
    best_score = 0
    for block_priority, block in enumerate(search_blocks):
        text = normal_text(block)
        if not text:
            continue
        for category in category_rules.get("categories", DEFAULT_CATEGORIES):
            for keyword in category_rules.get("keyword_rules", {}).get(category, []):
                score = _keyword_score(text, keyword)
                if score:
                    score += (2 - block_priority) * 100
                    if score > best_score:
                        best_score = score
                        best_category = category
    return best_category


def detect_brand(row, brand_rules=None):
    brand_rules = brand_rules or load_brand_rules()
    manual = _manual_match(row, brand_rules.get("manual_rules", {}))
    if manual:
        return manual

    title = normal_text(row.get("title", ""))
    for brand in sorted(brand_rules.get("brands", DEFAULT_BRANDS), key=len, reverse=True):
        brand_key = normal_text(brand)
        if brand_key and brand_key in title:
            return brand
    return ""


def save_category_manual_rule(row, category):
    category = clean_text(category)
    if not category:
        return
    data = load_category_rules()
    if category not in data["categories"]:
        data["categories"].append(category)
        data.setdefault("keyword_rules", {}).setdefault(category, [])
    for key in row_rule_keys(row):
        data.setdefault("manual_rules", {})[key] = category
    save_category_rules(data)


def save_brand_manual_rule(row, brand):
    brand = clean_text(brand)
    if not brand:
        return
    data = load_brand_rules()
    if normal_text(brand) not in {normal_text(b) for b in data["brands"]}:
        data["brands"].append(brand)
    for key in row_rule_keys(row):
        data.setdefault("manual_rules", {})[key] = brand
    save_brand_rules(data)
