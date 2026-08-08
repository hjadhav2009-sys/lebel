from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CatalogIdentifier, CatalogProduct


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
    """Indexed, account-scoped matcher that fetches at most two candidates."""

    def __init__(self, db: Session, account_id):
        self.db = db
        self.account_id = account_id

    def _by_sku(self, sku: str | None) -> list[CatalogProduct]:
        key = normalized(sku)
        if not key:
            return []
        query = (select(CatalogProduct).where(
            CatalogProduct.account_id == self.account_id,
            func.lower(func.trim(CatalogProduct.sku)) == key,
        ).order_by(CatalogProduct.id).limit(2))
        return list(self.db.scalars(query).all())

    def _by_identifier(self, kind: str, value: str | None, sku: str | None = None) -> list[CatalogProduct]:
        key = normalized(value)
        if not key:
            return []
        query = (select(CatalogProduct).join(CatalogIdentifier).where(
            CatalogProduct.account_id == self.account_id,
            func.lower(CatalogIdentifier.kind) == kind.casefold(),
            func.lower(func.trim(CatalogIdentifier.value)) == key,
        ))
        sku_key = normalized(sku)
        if sku_key:
            query = query.where(func.lower(func.trim(CatalogProduct.sku)) == sku_key)
        return list(self.db.scalars(query.distinct().order_by(CatalogProduct.id).limit(2)).all())

    @staticmethod
    def unique(matches: list[CatalogProduct], method: str, ambiguous_code: str) -> MatchResult:
        if len(matches) == 1:
            return MatchResult(matches[0], "matched", method)
        if len(matches) > 1:
            return MatchResult(None, "ambiguous", method, ambiguous_code)
        return MatchResult(None, "unmatched", method, "MISSING_CATALOG_MATCH")

    def amazon(self, sku: str | None, fnsku: str | None, asin: str | None) -> MatchResult:
        if sku:
            return self.unique(self._by_sku(sku), "SKU", "AMBIGUOUS_SKU_MATCH")
        if fnsku:
            result = self.unique(self._by_identifier("fnsku", fnsku), "FNSKU", "AMBIGUOUS_FNSKU_MATCH")
            if result.product or result.status == "ambiguous":
                return result
        if asin:
            return self.unique(self._by_identifier("asin", asin), "ASIN", "AMBIGUOUS_ASIN_MATCH")
        return MatchResult(None, "unmatched", None, "MISSING_CATALOG_MATCH")

    def flipkart(self, fsn: str | None, sku: str | None) -> MatchResult:
        if fsn and sku:
            result = self.unique(self._by_identifier("fsn", fsn, sku), "FSN+SKU", "AMBIGUOUS_FSN_SKU_MATCH")
            if result.product or result.status == "ambiguous":
                return result
        if fsn:
            result = self.unique(self._by_identifier("fsn", fsn), "FSN", "AMBIGUOUS_FSN_SKU_MATCH")
            if result.product or result.status == "ambiguous":
                return result
        if sku:
            return self.unique(self._by_sku(sku), "SKU", "AMBIGUOUS_FSN_SKU_MATCH")
        return MatchResult(None, "unmatched", None, "MISSING_CATALOG_MATCH")
