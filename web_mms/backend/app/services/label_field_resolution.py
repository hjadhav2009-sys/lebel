import re
from dataclasses import dataclass
from typing import Any

from app.models import ConsignmentLine

DISPLAY_NAMES = {
    "title":"Title","brand":"Brand","mrp":"MRP","format":"Format","generic_name":"Generic Name",
    "model_number":"Model Number","model_name":"Model Name","brand_color":"Brand Color","sales_package":"Sales Package",
    "sales_package_id":"Sales Package Id","base_material":"Base Material","body_material":"Body Material",
    "bangle_size":"Bangle Size","pack_of":"Pack Of","dimensions":"Dimensions","comment":"Comment","color":"Color",
    "plating":"Plating","diameter":"Diameter","type":"Type",
}
ALIASES = {
    "sales_package_identifier":"sales_package_id",
}


def canonical_field_key(value: object) -> str:
    key=re.sub(r"[^a-z0-9]+","_",str(value or "").strip().casefold()).strip("_")
    return ALIASES.get(key,key)


@dataclass(frozen=True)
class ResolvedLabelField:
    key: str
    value: Any
    source: str
    display_name: str

    def as_dict(self) -> dict:
        return {"value":self.value,"source":self.source,"display_name":self.display_name}


class CanonicalLabelFieldResolver:
    """Single priority-ordered contract for validation, snapshots, and renderers."""

    def __init__(self,line:ConsignmentLine):
        self.line=line;self.product=line.product;self.overrides=line.label_overrides or {}
        raw_fields=self.overrides.get("fields") or {}
        self.field_overrides={canonical_field_key(key):value for key,value in raw_fields.items()}
        for key,value in self.overrides.items():
            canonical=canonical_field_key(key)
            if key!="fields" and canonical in DISPLAY_NAMES:self.field_overrides[canonical]=value
        self.catalog_extras={canonical_field_key(key):value for key,value in ((self.product.extra_attributes if self.product else {}) or {}).items()}

    @staticmethod
    def _present(value:Any)->bool:
        return value is not None and (not isinstance(value,str) or bool(value.strip()))

    def _direct(self,key:str):
        values={
            "title":self.line.title_snapshot,
            "brand":self.line.brand_snapshot,
            "mrp":self.line.mrp_override if self.line.mrp_override is not None else self.line.mrp_catalog,
            "format":self.line.format_key,
        }
        return values.get(key)

    def _operational_override(self,key:str):
        if key=="mrp" and self.line.mrp_override is not None:return self.line.mrp_override
        return None

    def _catalog_core(self,key:str):
        if not self.product:return None
        return {"title":self.product.title,"brand":self.product.brand,"mrp":self.product.mrp}.get(key)

    def _derived(self,key:str):
        if key=="generic_name":return self.line.category_snapshot or (self.product.category if self.product else None)
        return None

    def resolve(self,name:object)->ResolvedLabelField:
        key=canonical_field_key(name);display=DISPLAY_NAMES.get(key,str(name).strip().replace("_"," ").title())
        candidates=((self.field_overrides.get(key),"Consignment Override"),(self._operational_override(key),"Consignment Override"),(self._direct(key),"Catalog"),
            (self._catalog_core(key),"Catalog"),(self.catalog_extras.get(key),"Catalog"),(self._derived(key),"Derived"))
        for value,source in candidates:
            if self._present(value):return ResolvedLabelField(key,value,source,display)
        return ResolvedLabelField(key,None,"Missing",display)

    def resolve_many(self,names:list[object])->dict[str,ResolvedLabelField]:
        return {canonical_field_key(name):self.resolve(name) for name in names}

    def all_effective(self,required:list[object]|None=None)->dict[str,ResolvedLabelField]:
        keys=set(DISPLAY_NAMES)|set(self.catalog_extras)|set(self.field_overrides)
        keys.update(canonical_field_key(value) for value in (required or []))
        return {key:self.resolve(key) for key in sorted(keys)}
