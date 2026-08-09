from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import CatalogIdentifier, CatalogProduct, Marketplace, MarketplaceAccount
from app.renderers.amazon_dynamic_tspl_v1 import AmazonDynamicTSPLRenderer
from app.renderers.amazon_dynamic_tspl_v2 import AmazonDynamicTSPLRendererV2
from app.renderers.base import RendererError, format_mrp, plan_two_up
from app.renderers.flipkart_hybrid_tspl_v1 import FORMAT_FIELDS, FlipkartHybridTSPLRenderer
from app.renderers.flipkart_hybrid_tspl_v2 import FlipkartHybridTSPLRendererV2
from app.renderers.font_registry import FONT_PATHS
from app.services.consignment_matching import ConsignmentMatcher


def font_path() -> str:
    candidates=(Path("C:/Windows/Fonts/arial.ttf"),Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"))
    return str(next(path for path in candidates if path.is_file()))


def amazon_snapshot(copies=1):
    return {"sku":"SKU-1","fnsku":"X001ABC","asin":"B001ABC","title":"Gold Key Chain","brand":"MMS","mrp":"799",
        "net_quantity":{"value":1,"unit":"N"},"generic_name":"Key Chain","print_quantity":copies,
        "address_profile":{"marketed_by":"MMS Retail","address_line_1":"Mumbai","city_state":"Maharashtra"}}


def flipkart_snapshot(format_key="key_chain", copies=1):
    fields={name:"Value" for name in FORMAT_FIELDS[format_key]}; fields["Dimensions"]="10 x 5 x 2 cm"; fields["Generic Name"]="Jewellery"
    return {"format":format_key,"fsn":"FSN12345","mrp":"499","net_quantity":{"value":1,"unit":"N"},"generic_name":"Jewellery",
        "label_fields":fields,"print_quantity":copies}


def profile(renderer="amazon_dynamic_tspl_v1"):
    config: dict[str, object]={"approved_dpi":203}
    if renderer.startswith("flipkart"): config.update({"font_path":font_path(),"font_sizes":[12,11,10],"barcode_y":300})
    return {"dpi":203,"media_width_mm":101.5,"media_height_mm":50,"gap_mm":2,"renderer":renderer,"layout_version":1,"config":config}


def test_amazon_renderer_is_deterministic_and_uses_native_barcode():
    renderer=AmazonDynamicTSPLRenderer(); first=renderer.render([amazon_snapshot(3)],profile()); second=renderer.render([amazon_snapshot(3)],profile())
    assert first.raw_bytes==second.raw_bytes and b"BARCODE" in first.raw_bytes and first.label_count==3
    assert first.diagnostics["odd_final_label"] is True


@pytest.mark.parametrize("format_key", sorted(FORMAT_FIELDS))
def test_all_flipkart_formats_compile_with_raster_text_and_native_barcode(format_key):
    result=FlipkartHybridTSPLRenderer().render([flipkart_snapshot(format_key)],profile("flipkart_hybrid_tspl_v1"))
    assert b"BITMAP" in result.raw_bytes and b"BARCODE" in result.raw_bytes and result.label_count==1


def test_flipkart_overflow_blocks_instead_of_clipping():
    snapshot=flipkart_snapshot(); snapshot["label_fields"]={key:"very long product attribute "*30 for key in snapshot["label_fields"]}
    with pytest.raises(RendererError,match="LABEL_TEXT_OVERFLOW"): FlipkartHybridTSPLRenderer().render([snapshot],profile("flipkart_hybrid_tspl_v1"))


def test_missing_font_blocks_production_render():
    broken=profile("flipkart_hybrid_tspl_v1"); broken["config"]["font_path"]="missing-font.ttf"
    with pytest.raises(RendererError,match="FONT_NOT_AVAILABLE"): FlipkartHybridTSPLRenderer().render([flipkart_snapshot()],broken)


def test_shared_mrp_format_and_two_up_odd_label_contract():
    assert format_mrp("99.9")=="Rs.99.90 (inclusive of all Taxes)"
    pages=plan_two_up([amazon_snapshot(3)]); assert len(pages)==2 and pages[-1][1] is None


def test_matcher_queries_are_bounded_and_do_not_load_account_catalog():
    engine=create_engine("sqlite+pysqlite:///:memory:"); Base.metadata.create_all(engine); statements=[]
    event.listen(engine,"before_cursor_execute",lambda _c,_cu,s,_p,_ctx,_many: statements.append(s))
    with Session(engine) as db:
        owner=MarketplaceAccount(marketplace=Marketplace.AMAZON,name="Scale"); db.add(owner); db.flush()
        for index in range(250):
            row=CatalogProduct(account_id=owner.id,business_key=f"sku:{index}",row_hash=f"{index:064}",sku=f"SKU-{index}",extra_attributes={}); db.add(row); db.flush()
            db.add(CatalogIdentifier(product_id=row.id,kind="fnsku",value=f"F-{index}",source="test"))
        db.flush(); statements.clear(); assert ConsignmentMatcher(db,owner.id).amazon("SKU-249",None,None).product is not None
    selects=[value.lower() for value in statements if value.lstrip().lower().startswith("select")]
    assert selects and all(" limit " in value for value in selects)


def test_v2_five_copy_expansion_has_three_pairs_and_no_sixth_label(monkeypatch):
    amazon=AmazonDynamicTSPLRendererV2().render([amazon_snapshot(5)],profile("amazon_dynamic_tspl_v2"))
    monkeypatch.setitem(FONT_PATHS,"mms_default_sans",[Path(font_path())])
    flip_profile=profile("flipkart_hybrid_tspl_v2");flip_profile["config"].pop("font_path");flip_profile["config"]["font_key"]="mms_default_sans"
    flipkart=FlipkartHybridTSPLRendererV2().render([flipkart_snapshot(copies=5)],flip_profile)
    assert amazon.label_count==flipkart.label_count==5
    assert amazon.diagnostics["pairs"]==flipkart.diagnostics["pairs"]==3
    assert amazon.diagnostics["odd_final_label"] is flipkart.diagnostics["odd_final_label"] is True
    assert amazon.raw_bytes.count(b"PRINT 1,1")==flipkart.raw_bytes.count(b"PRINT 1,1")==3


def test_flipkart_v2_diagnostics_capture_logical_font_identity(monkeypatch):
    monkeypatch.setitem(FONT_PATHS,"mms_default_sans",[Path(font_path())]);config=profile("flipkart_hybrid_tspl_v2");config["config"].pop("font_path");config["config"]["font_key"]="mms_default_sans"
    result=FlipkartHybridTSPLRendererV2().render([flipkart_snapshot()],config)
    assert result.diagnostics["layout"]["font_key"]=="mms_default_sans"
    assert len(result.diagnostics["layout"]["font_sha256"])==64


def test_phase3_migration_is_explicit_and_stacked():
    migration=Path("alembic/versions/20260810_0003_print_agent_renderer.py").read_text()
    assert 'down_revision = "20260809_0002"' in migration
    assert "print_artifacts" in migration and "renderer_profile_approvals" in migration and "agent_pairing_codes" in migration
    assert "lower(btrim(sku))" in migration
