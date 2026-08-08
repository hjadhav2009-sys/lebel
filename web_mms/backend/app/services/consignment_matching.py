from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import CatalogProduct


def normalized(value: object | None) -> str | None:
    text = " ".join(str(value or "").strip().split()).casefold()
    return text or None


@dataclass(frozen=True)
class MatchResult:
    product: CatalogProduct | None
    status: str
    method: str | None
    error_code: str | None = None


class ConsignmentMatcher:
    """Account-scoped matcher. Exact seller identifiers always precede fallbacks."""

    def __init__(self, db: Session, account_id):
        self.products = list(db.scalars(
            select(CatalogProduct).where(CatalogProduct.account_id == account_id)
            .options(selectinload(CatalogProduct.identifiers))
        ).all())

    def _by_sku(self, sku: str | None) -> list[CatalogProduct]:
        key = normalized(sku)
        return [p for p in self.products if normalized(p.sku) == key] if key else []

    def _by_identifier(self, kind: str, value: str | None) -> list[CatalogProduct]:
        key = normalized(value)
        if not key:
            return []
        return [p for p in self.products if any(i.kind.casefold() == kind and normalized(i.value) == key for i in p.identifiers)]

    @staticmethod
    def unique(matches: list[CatalogProduct], method: str, ambiguous_code: str) -> MatchResult:
        unique = {p.id: p for p in matches}
        if len(unique) == 1:
            return MatchResult(next(iter(unique.values())), "matched", method)
        if len(unique) > 1:
            return MatchResult(None, "ambiguous", method, ambiguous_code)
        return MatchResult(None, "unmatched", method, "MISSING_CATALOG_MATCH")

    def amazon(self, sku: str | None, fnsku: str | None, asin: str | None) -> MatchResult:
        if sku:
            # Seller SKU is the Amazon business identity. A present SKU must never
            # fall through to ASIN and accidentally merge two seller listings.
            return self.unique(self._by_sku(sku), "SKU", "AMBIGUOUS_SKU_MATCH")
        if fnsku:
            result = self.unique(self._by_identifier("fnsku", fnsku), "FNSKU", "AMBIGUOUS_FNSKU_MATCH")
            if result.product or result.status == "ambiguous":
                return result
        if asin:
            return self.unique(self._by_identifier("asin", asin), "ASIN", "AMBIGUOUS_ASIN_MATCH")
        return MatchResult(None, "unmatched", None, "MISSING_CATALOG_MATCH")

    def flipkart(self, fsn: str | None, sku: str | None) -> MatchResult:
        fsn_matches = self._by_identifier("fsn", fsn)
        sku_matches = self._by_sku(sku)
        if fsn and sku:
            exact = [p for p in fsn_matches if p in sku_matches]
            result = self.unique(exact, "FSN+SKU", "AMBIGUOUS_FSN_SKU_MATCH")
            if result.product or result.status == "ambiguous":
                return result
        if fsn:
            result = self.unique(fsn_matches, "FSN", "AMBIGUOUS_FSN_SKU_MATCH")
            if result.product or result.status == "ambiguous":
                return result
        if sku:
            return self.unique(sku_matches, "SKU", "AMBIGUOUS_FSN_SKU_MATCH")
        return MatchResult(None, "unmatched", None, "MISSING_CATALOG_MATCH")
