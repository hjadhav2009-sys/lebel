from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AddressProfile, ConsignmentIssue, ConsignmentLine, LabelFormatProfile, Marketplace


class ConsignmentValidationService:
    def __init__(self, db: Session): self.db = db

    def validate(self, line: ConsignmentLine) -> list[ConsignmentIssue]:
        self.db.execute(delete(ConsignmentIssue).where(ConsignmentIssue.consignment_line_id == line.id, ConsignmentIssue.resolved.is_(False)))
        problems: list[tuple[str, str, str | None, str]] = []
        if not line.product_id: problems.append(("blocking", "MISSING_CATALOG_MATCH", None, "No account-scoped catalog product matched this line."))
        if line.mrp_override is None and line.mrp_catalog is None: problems.append(("blocking", "MISSING_MRP", "mrp", "MRP is required."))
        mrp = line.mrp_override if line.mrp_override is not None else line.mrp_catalog
        if mrp is not None and Decimal(mrp) <= 0: problems.append(("blocking", "INVALID_MRP", "mrp", "MRP must be positive."))
        if line.print_quantity <= 0: problems.append(("blocking", "INVALID_PRINT_QTY", "print_quantity", "Print quantity must be a positive integer."))
        if line.net_quantity_value < 1 or not line.net_quantity_unit: problems.append(("blocking", "INVALID_NET_QTY", "net_quantity", "Net quantity needs a value of at least 1 and a unit."))
        if not line.format_key: problems.append(("blocking", "MISSING_LABEL_FORMAT", "format_key", "Select a label format."))
        if line.consignment.marketplace == Marketplace.AMAZON and not line.fnsku: problems.append(("blocking", "MISSING_FNSKU", "fnsku", "Amazon labels require an FNSKU."))
        if line.consignment.marketplace == Marketplace.FLIPKART and not line.fsn: problems.append(("blocking", "MISSING_FSN", "fsn", "Flipkart labels require an FSN."))
        address_id = line.address_profile_id or line.consignment.account.default_address_profile_id
        address = self.db.get(AddressProfile, address_id) if address_id else None
        if not address or address.account_id != line.consignment.account_id:
            problems.append(("blocking", "MISSING_ADDRESS_PROFILE", "address_profile", "Select an address profile owned by this marketplace account."))
        if line.format_key:
            profile = self.db.scalar(select(LabelFormatProfile).where(LabelFormatProfile.key == line.format_key, LabelFormatProfile.is_active.is_(True), (LabelFormatProfile.account_id == line.consignment.account_id) | (LabelFormatProfile.account_id.is_(None))))
            if profile:
                available = self._available(line)
                for field in profile.required_fields:
                    if not available.get(str(field)):
                        problems.append(("blocking", "MISSING_REQUIRED_FIELD", str(field), f"Required label field '{field}' is missing."))
        issues = [ConsignmentIssue(consignment_id=line.consignment_id, consignment_line_id=line.id, severity=s, code=c, field=f, message=m) for s, c, f, m in problems]
        self.db.add_all(issues)
        line.error_count = len(issues)
        if any(i.severity == "blocking" for i in issues) and line.workflow_state == "to_print": line.workflow_state = "blocked"
        elif not issues and line.workflow_state == "blocked": line.workflow_state = "to_print"
        return issues

    @staticmethod
    def _available(line: ConsignmentLine) -> dict:
        product = line.product
        values = dict(product.extra_attributes if product else {})
        values.update({"Brand": line.label_overrides.get("brand") or line.brand_snapshot, "Model Number": line.label_overrides.get("model_number"), "Model Name": line.label_overrides.get("model_name")})
        values.update(line.label_overrides.get("fields", {}))
        return values
