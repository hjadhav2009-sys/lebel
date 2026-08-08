from typing import Any

from app.services.amazon_consignment_service import positive_quantity
from app.services.consignment_matching import ConsignmentMatcher

ALIASES = {"fsn": {"fsn"}, "sku": {"sku", "sku id", "seller sku"}, "quantity": {"quantity sent", "quantity", "qty sent", "qty"}}


class FlipkartQuantityMatcher:
    def __init__(self, matcher: ConsignmentMatcher): self.matcher = matcher

    def normalize(self, row: dict[str, Any]) -> dict[str, Any]:
        lookup = {" ".join(str(k).strip().split()).casefold(): v for k, v in row.items()}
        value = lambda name: next((lookup[k] for k in ALIASES[name] if lookup.get(k) not in (None, "")), None)
        fsn, sku, quantity = value("fsn"), value("sku"), positive_quantity(value("quantity"))
        match = self.matcher.flipkart(str(fsn) if fsn else None, str(sku) if sku else None)
        return {"fsn": fsn, "merchant_sku": sku, "source_quantity": quantity, "print_quantity": quantity,
            "product": match.product, "match_status": match.status, "match_method": match.method, "match_error": match.error_code}
