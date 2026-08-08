from typing import Any

from app.services.consignment_matching import ConsignmentMatcher

ALIASES = {
    "merchant_sku": {"merchant sku", "seller sku", "sku"}, "title": {"title", "product title"},
    "asin": {"asin"}, "fnsku": {"fnsku"}, "quantity": {"shipped", "quantity shipped"},
}


def _value(row: dict[str, Any], field: str):
    lookup = {" ".join(str(k).strip().split()).casefold(): v for k, v in row.items()}
    return next((lookup[k] for k in ALIASES[field] if lookup.get(k) not in (None, "")), None)


class AmazonConsignmentService:
    def __init__(self, matcher: ConsignmentMatcher): self.matcher = matcher

    def normalize(self, row: dict[str, Any]) -> dict[str, Any]:
        sku, asin, fnsku = (_value(row, key) for key in ("merchant_sku", "asin", "fnsku"))
        quantity = positive_quantity(_value(row, "quantity"))
        match = self.matcher.amazon(str(sku) if sku else None, str(fnsku) if fnsku else None, str(asin) if asin else None)
        product = match.product
        return {"merchant_sku": sku, "asin": asin, "fnsku": fnsku, "title_snapshot": _value(row, "title") or (product.title if product else None),
            "source_quantity": quantity, "print_quantity": quantity, "product": product, "match_status": match.status,
            "match_method": match.method, "match_error": match.error_code}


def positive_quantity(value: object) -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("INVALID_PRINT_QTY") from exc
    if number <= 0:
        raise ValueError("INVALID_PRINT_QTY")
    return number
