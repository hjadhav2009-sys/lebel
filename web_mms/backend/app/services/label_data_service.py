from copy import deepcopy
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import AddressProfile, ConsignmentLine
from app.services.label_field_resolution import CanonicalLabelFieldResolver


class ConsignmentLabelDataService:
    def __init__(self, db: Session): self.db = db

    @staticmethod
    def _resolved(value, source: str): return {"value": value, "source": source if value not in (None, "") else "Missing"}

    def resolve(self, line: ConsignmentLine) -> dict:
        overrides = deepcopy(line.label_overrides or {})
        address_id = line.address_profile_id or line.consignment.account.default_address_profile_id
        address = self.db.get(AddressProfile, address_id) if address_id else None
        if address and address.account_id != line.consignment.account_id:
            address = None
        required=[]
        if line.format_key:
            from sqlalchemy import select
            from app.models import LabelFormatProfile
            profile=self.db.scalar(select(LabelFormatProfile).where(LabelFormatProfile.key==line.format_key,LabelFormatProfile.is_active.is_(True),
                (LabelFormatProfile.account_id==line.consignment.account_id)|(LabelFormatProfile.account_id.is_(None))))
            required=list(profile.required_fields or []) if profile else []
        resolver=CanonicalLabelFieldResolver(line);fields={key:value.as_dict() for key,value in resolver.all_effective(required).items()}
        fields["net_quantity"]=self._resolved({"value":line.net_quantity_value,"unit":line.net_quantity_unit},"Consignment Override" if "net_quantity" in overrides else "Derived")
        address_payload = None if not address else {"id": str(address.id), "name": address.name, "marketed_by": address.marketed_by, "address_line_1": address.address_line_1, "address_line_2": address.address_line_2, "city_state": address.city_state, "email": address.email, "phone": address.phone, "origin": address.origin}
        return {"fields": fields, "address_profile": address_payload}

    def snapshot(self, line: ConsignmentLine) -> dict:
        resolved = self.resolve(line)
        payload = {"marketplace": line.consignment.marketplace.value, "account": {"id": str(line.consignment.account.id), "name": line.consignment.account.name},
            "consignment": {"id": str(line.consignment.id), "name": line.consignment.name}, "product_id": str(line.product_id) if line.product_id else None,
            "consignment_line_id": str(line.id), "sku": line.merchant_sku, "asin": line.asin, "fnsku": line.fnsku, "fsn": line.fsn,
            "listing_id": line.listing_id, "title": resolved["fields"]["title"]["value"], "brand": resolved["fields"]["brand"]["value"],
            "mrp": str(resolved["fields"]["mrp"]["value"]) if isinstance(resolved["fields"]["mrp"]["value"], Decimal) else resolved["fields"]["mrp"]["value"],
            "net_quantity": {"value": line.net_quantity_value, "unit": line.net_quantity_unit}, "print_quantity": line.print_quantity,
            "format": line.format_key, "generic_name": resolved["fields"]["generic_name"]["value"], "address_profile": resolved["address_profile"],
            "label_fields": {k: v["value"] for k, v in resolved["fields"].items()}, "field_sources": {k: v["source"] for k, v in resolved["fields"].items()},
            "field_metadata":resolved["fields"],"snapshot_version":"phase3.1-canonical-v1"}
        return _json_safe(payload)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value
