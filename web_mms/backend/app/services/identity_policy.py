from dataclasses import dataclass


def canonical_identifier(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


@dataclass(frozen=True)
class IdentityDecision:
    business_key: str
    warnings: tuple[str, ...] = ()


class IdentityPolicy:
    """Account-scoped product identity. Secondary IDs never silently merge SKUs."""

    @staticmethod
    def decide(marketplace: str, sku: str | None, identifiers: dict[str, str]) -> IdentityDecision:
        if sku and sku.strip():
            return IdentityDecision(f"{marketplace}:sku:{canonical_identifier(sku)}")
        fallback_order = ("listing_id", "fsn") if marketplace == "flipkart" else ("fnsku", "asin")
        for kind in fallback_order:
            value = identifiers.get(kind)
            if value:
                return IdentityDecision(
                    f"{marketplace}:{kind}:{canonical_identifier(value)}",
                    (f"missing_seller_sku: matched by {kind}",),
                )
        raise ValueError("A stable seller SKU or marketplace identifier is required")

    @staticmethod
    def secondary_conflicts(
        incoming: dict[str, str], existing_by_kind: dict[str, set[str]]
    ) -> list[str]:
        warnings = []
        for kind, value in incoming.items():
            known = existing_by_kind.get(kind, set())
            if known and canonical_identifier(value) not in {canonical_identifier(item) for item in known}:
                warnings.append(f"conflicting_{kind}")
        return warnings
