from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.auth import CurrentPrincipal, require_roles
from app.core.config import Settings
from app.models import CatalogProduct, ConsignmentLine
from app.renderers.amazon_dynamic_tspl_v2 import AmazonDynamicTSPLRendererV2
from app.renderers.base import RendererError
from app.services.label_field_resolution import CanonicalLabelFieldResolver, canonical_field_key


def amazon_snapshot():
    return {"sku":"SKU-1","fnsku":"X001ABC","title":"Gold Key Chain","brand":"MMS","mrp":"799","net_quantity":{"value":1,"unit":"N"},"generic_name":"Key Chain","print_quantity":1,"address_profile":{"marketed_by":"MMS Retail","address_line_1":"Mumbai","city_state":"Maharashtra","email":"care@example.com","phone":"9999999999","origin":"India"}}


def amazon_profile():
    return {"dpi":203,"media_width_mm":101.5,"media_height_mm":50,"gap_mm":2,"layout_version":2,"config":{}}


def test_canonical_keys_and_resolution_priority_are_shared():
    assert canonical_field_key("Model-Name") == canonical_field_key(" model_name ") == "model_name"
    product=CatalogProduct(account_id=None,business_key="sku:x",row_hash="x"*64,title="Catalog title",brand="Catalog brand",mrp=Decimal("500"),extra_attributes={"Model Name":"Pendant One","Product Dimensions":"shipping-only"})
    line=ConsignmentLine(product=product,title_snapshot="Catalog title",brand_snapshot="Catalog brand",mrp_catalog=Decimal("500"),mrp_override=Decimal("450"),label_overrides={"fields":{"MODEL-NAME":"Override model"}})
    resolver=CanonicalLabelFieldResolver(line)
    assert resolver.resolve("model name").value == "Override model"
    assert resolver.resolve("model name").source == "Consignment Override"
    assert resolver.resolve("mrp").source == "Consignment Override"
    assert resolver.resolve("product_dimensions").source == "Catalog"
    assert resolver.resolve("dimensions").source == "Missing"


def test_amazon_v2_contains_full_desktop_parity_content_and_native_barcode():
    renderer=AmazonDynamicTSPLRendererV2();result=renderer.render([amazon_snapshot()],amazon_profile());raw=result.raw_bytes.decode("cp1252")
    for text in ["Product Information","Brand: MMS","SKU No / Merchant SKU: SKU-1","Net Quantity: 1 N","Generic Name: Key Chain","Manufactured by / Marketed By /","Customer care Details:","Email Id: care@example.com","Contact: 9999999999","Origin: India","X001ABC","Gold Key Chain"]:assert text in raw
    assert "BARCODE" in raw and "ASIN" not in raw and renderer.key=="amazon_dynamic_tspl_v2"


def test_amazon_v2_overflow_blocks_and_v1_is_not_mutated():
    snapshot=amazon_snapshot();snapshot["title"]="x"*100
    with pytest.raises(RendererError,match="LABEL_TEXT_OVERFLOW"):AmazonDynamicTSPLRendererV2().render([snapshot],amazon_profile())


def test_rbac_and_real_transport_gate_fail_closed():
    packing=CurrentPrincipal(None,"packing@example.com","Packing",frozenset({"Packing"}))
    with pytest.raises(HTTPException) as denied:require_roles("Admin")(packing)
    assert denied.value.status_code==403
    with pytest.raises(ValueError,match="LOCAL_AUTH"):Settings(print_transport_enabled=True).validate_transport_gate()
    with pytest.raises(ValueError,match="STRONG_SECRET"):Settings(print_transport_enabled=True,auth_mode="local",auth_cookie_secure=True).validate_transport_gate()
    Settings(print_transport_enabled=False).validate_transport_gate()
