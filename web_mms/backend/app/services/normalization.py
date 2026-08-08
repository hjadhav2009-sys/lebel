import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable


def _header(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


AMAZON_TECHNICAL = {
    "sku": re.compile(r"^contribution_sku#1\.value$", re.I),
    "product_id": re.compile(r"^amzn1\.volt\.ca\.product_id_value$", re.I),
    "brand": re.compile(r"^brand\[.*\]#1\.value$", re.I),
    "title": re.compile(r"^(item_name|product_title)\[.*\]#1\.value$", re.I),
    "mrp": re.compile(r"^purchasable_offer\[.*\]#1\.maximum_retail_price#1\.schedule#1\.value_with_tax$", re.I),
    "main_image": re.compile(r"^main_product_image_locator\[.*\]#1\.media_location$", re.I),
    "other_image": re.compile(r"^other_product_image_locator_[1-8]\[.*\]#1\.media_location$", re.I),
}

ALIASES = {
    "sku": {"sku", "seller sku", "merchant sku", "sku id"},
    "product_id": {"product id", "asin"},
    "fnsku": {"fnsku"},
    "fsn": {"fsn"},
    "listing_id": {"listing id", "listing_id"},
    "title": {"title", "product name", "item name"},
    "brand": {"brand", "brand name"},
    "mrp": {"mrp", "maximum retail price"},
    "fsp": {"fsp", "selling price"},
    "category": {"category", "format", "product type"},
    "main_image": {"main image url", "main image", "image url"},
}


@dataclass(slots=True)
class NormalizedProduct:
    marketplace: str
    sku: str | None
    title: str | None = None
    brand: str | None = None
    mrp: str | None = None
    category: str | None = None
    identifiers: dict[str, str] = field(default_factory=dict)
    images: list[str] = field(default_factory=list)
    extra_attributes: dict[str, Any] = field(default_factory=dict)
    source_template: str | None = None
    source_category: str | None = None

    def business_key(self) -> str:
        candidates = (("sku", self.sku), ("fsn", self.identifiers.get("fsn")), ("asin", self.identifiers.get("asin")), ("listing_id", self.identifiers.get("listing_id")))
        for kind, value in candidates:
            if value:
                return f"{self.marketplace}:{kind}:{value.strip().casefold()}"
        raise ValueError("A stable identifier (SKU, FSN, ASIN, or Listing ID) is required")

    def row_hash(self) -> str:
        payload = asdict(self)
        payload["images"] = sorted(set(payload["images"]))
        payload["identifiers"] = dict(sorted(payload["identifiers"].items()))
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def detect_header_row(rows: list[list[Any]], marketplace: str, scan_limit: int = 20) -> int:
    best_index, best_score = -1, 0
    for index, row in enumerate(rows[:scan_limit]):
        values = [_header(value) for value in row]
        if marketplace == "amazon":
            technical = sum(any(pattern.match(value) for pattern in AMAZON_TECHNICAL.values()) for value in values)
            aliases = sum(value in ALIASES["sku"] | ALIASES["mrp"] | ALIASES["product_id"] for value in values)
            score = technical * 10 + aliases
        else:
            score = sum(value in ALIASES["sku"] | ALIASES["fsn"] | ALIASES["listing_id"] | ALIASES["mrp"] for value in values)
        if score > best_score:
            best_index, best_score = index, score
    if best_index < 0 or best_score < 2:
        raise ValueError("Could not detect a supported header row")
    return best_index


def _find_columns(headers: Iterable[Any], marketplace: str) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    normalized = [_header(header) for header in headers]
    if marketplace == "amazon":
        for index, header in enumerate(normalized):
            for field_name, pattern in AMAZON_TECHNICAL.items():
                if pattern.match(header):
                    found.setdefault(field_name, []).append(index)
        # Technical keys win; aliases fill gaps only.
    for field_name, aliases in ALIASES.items():
        if field_name in found:
            continue
        for index, header in enumerate(normalized):
            if header in aliases:
                found.setdefault(field_name, []).append(index)
    return found


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _money(value: Any) -> str | None:
    text = _clean(value)
    if text is None:
        return None
    try:
        return format(Decimal(text.replace(",", "").replace("₹", "")).quantize(Decimal("0.01")), "f")
    except InvalidOperation as exc:
        raise ValueError(f"Invalid MRP: {text}") from exc


def normalize_row(headers: list[Any], values: list[Any], marketplace: str, *, source_template: str | None = None, source_category: str | None = None) -> NormalizedProduct:
    columns = _find_columns(headers, marketplace)

    def first(name: str) -> str | None:
        for index in columns.get(name, []):
            if index < len(values) and _clean(values[index]):
                return _clean(values[index])
        return None

    identifiers: dict[str, str] = {}
    if marketplace == "amazon":
        if first("product_id"):
            identifiers["asin"] = first("product_id") or ""
        if first("fnsku"):
            identifiers["fnsku"] = first("fnsku") or ""
    else:
        for kind in ("fsn", "listing_id"):
            if first(kind):
                identifiers[kind] = first(kind) or ""

    mapped_indexes = {i for indexes in columns.values() for i in indexes}
    extras = {_header(headers[i]): values[i] for i in range(min(len(headers), len(values))) if i not in mapped_indexes and _clean(values[i]) is not None}
    images = []
    for field_name in ("main_image", "other_image"):
        for index in columns.get(field_name, []):
            if index < len(values) and _clean(values[index]):
                images.append(_clean(values[index]) or "")

    return NormalizedProduct(
        marketplace=marketplace,
        sku=first("sku"), title=first("title"), brand=first("brand"), mrp=_money(first("mrp")),
        category=first("category") or source_category, identifiers=identifiers, images=list(dict.fromkeys(images)),
        extra_attributes=extras, source_template=source_template, source_category=source_category,
    )


def flipkart_product_url(fsn: str) -> str:
    return f"https://www.flipkart.com/product/p/itme?pid={fsn}"


def classify_snapshots(existing: dict[str, str], incoming: Iterable[NormalizedProduct]) -> dict[str, int]:
    """Pure planning helper used by previews and large-import tests."""
    counts = {"new": 0, "updated": 0, "unchanged": 0, "errors": 0}
    seen_identifiers: set[tuple[str, str]] = set()
    for row in incoming:
        try:
            key, digest = row.business_key(), row.row_hash()
            for kind, value in row.identifiers.items():
                marker = kind, value.casefold()
                if marker in seen_identifiers:
                    raise ValueError(f"Duplicate {kind}: {value}")
                seen_identifiers.add(marker)
            counts["new" if key not in existing else "unchanged" if existing[key] == digest else "updated"] += 1
        except ValueError:
            counts["errors"] += 1
    return counts
