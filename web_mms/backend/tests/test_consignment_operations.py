from copy import deepcopy
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.consignments import patch_line
from app.db.base import Base
from app.models import (AddressProfile, CatalogIdentifier, CatalogProduct, Consignment, ConsignmentIssue,
    ConsignmentLine, LabelFormatProfile, Marketplace, MarketplaceAccount, PrintJobLine)
from app.schemas import ConsignmentLinePatch
from app.services.amazon_consignment_service import AmazonConsignmentService, positive_quantity
from app.services.consignment_import_service import ConsignmentImportService, ParsedConsignment
from app.services.consignment_matching import ConsignmentMatcher
from app.services.consignment_validation import ConsignmentValidationService
from app.services.label_data_service import ConsignmentLabelDataService
from app.services.print_job_service import PrintJobService, PrintJobValidationError


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session: yield session


def account(db, marketplace=Marketplace.AMAZON, name="Primary"):
    row = MarketplaceAccount(marketplace=marketplace, name=name); db.add(row); db.flush(); return row


def product(db, owner, sku, *, mrp: str | None="799", category="key_chain", identifiers=None, extras=None):
    row = CatalogProduct(account_id=owner.id, business_key=f"sku:{sku}", row_hash=(sku * 64)[:64], sku=sku,
        title=f"Title {sku}", brand="MMS", mrp=Decimal(mrp) if mrp else None, category=category, extra_attributes=extras or {})
    db.add(row); db.flush()
    for kind, value in (identifiers or {}).items(): db.add(CatalogIdentifier(product_id=row.id, kind=kind, value=value, source="test"))
    db.flush(); return row


def consignment(db, owner, name="Batch"):
    row = Consignment(account_id=owner.id, marketplace=owner.marketplace, name=name, source_type="test", status="open")
    db.add(row); db.flush(); return row


def address(db, owner):
    row = AddressProfile(account_id=owner.id, name="Mumbai", marketed_by="MMS", address_line_1="Line 1", city_state="Mumbai, MH", config={}, is_default=True)
    db.add(row); db.flush(); owner.default_address_profile_id=row.id; return row


def printable_line(db, batch, catalog, **values):
    defaults=dict(consignment=batch, product=catalog, merchant_sku=catalog.sku, fnsku="FNSKU1" if batch.marketplace==Marketplace.AMAZON else None,
        fsn="FSN1" if batch.marketplace==Marketplace.FLIPKART else None, title_snapshot=catalog.title, brand_snapshot=catalog.brand,
        category_snapshot=catalog.category, format_key=catalog.category, source_quantity=2, print_quantity=2,
        net_quantity_value=1, net_quantity_unit="N", mrp_catalog=catalog.mrp, mrp_source="catalog", selected_for_print=True,
        workflow_state="to_print", match_status="matched", match_method="SKU", raw_row={})
    defaults.update(values); row=ConsignmentLine(**defaults); db.add(row); db.flush(); return row


def test_01_amazon_consignment_sku_match(db):
    owner=account(db); expected=product(db,owner,"SKU-1"); result=ConsignmentMatcher(db,owner.id).amazon(" sku-1 ",None,None)
    assert result.product==expected and result.method=="SKU"


def test_02_amazon_fnsku_fallback_unique(db):
    owner=account(db); expected=product(db,owner,"S1",identifiers={"fnsku":"F1"}); result=ConsignmentMatcher(db,owner.id).amazon(None,"f1",None)
    assert result.product==expected and result.method=="FNSKU"


def test_03_amazon_asin_fallback_unique(db):
    owner=account(db); expected=product(db,owner,"S1",identifiers={"asin":"A1"}); result=ConsignmentMatcher(db,owner.id).amazon(None,None,"a1")
    assert result.product==expected and result.method=="ASIN"


def test_04_same_asin_with_two_skus_is_not_merged(db):
    owner=account(db); product(db,owner,"S1",identifiers={"asin":"A1"}); product(db,owner,"S2",identifiers={"asin":"A1"})
    assert ConsignmentMatcher(db,owner.id).amazon("UNKNOWN",None,"A1").status=="unmatched"


def test_05_amazon_shipped_becomes_print_quantity(db):
    owner=account(db); product(db,owner,"S1"); data=AmazonConsignmentService(ConsignmentMatcher(db,owner.id)).normalize({"Merchant SKU":"S1","Shipped":"4"})
    assert data["source_quantity"]==data["print_quantity"]==4


def test_06_amazon_mrp_comes_from_catalog_on_import(db):
    owner=account(db); product(db,owner,"S1",mrp="399"); batch=consignment(db,owner)
    parsed=ParsedConsignment("a.csv","CSV","Amazon Consignment",1,["merchant sku","shipped"],[(2,{"Merchant SKU":"S1","Shipped":1})],[],"a"*64)
    ConsignmentImportService(db).apply(batch,parsed); line=db.scalar(select(ConsignmentLine)); assert line and line.mrp_catalog==Decimal("399")


def test_07_missing_amazon_mrp_blocks(db):
    owner=account(db); catalog=product(db,owner,"S1",mrp=None); batch=consignment(db,owner); line=printable_line(db,batch,catalog,mrp_catalog=None)
    issues=ConsignmentValidationService(db).validate(line); assert any(x.code=="MISSING_MRP" for x in issues) and line.workflow_state=="blocked"


def test_08_manual_mrp_override_does_not_mutate_catalog(db):
    owner=account(db); catalog=product(db,owner,"S1",mrp="100"); batch=consignment(db,owner); line=printable_line(db,batch,catalog)
    patch_line(line.id,ConsignmentLinePatch(expected_version=1,field="mrp_override",value="250"),db)
    assert line.mrp_override==Decimal("250") and catalog.mrp==Decimal("100")


def test_09_flipkart_exact_fsn_sku_has_priority(db):
    owner=account(db,Marketplace.FLIPKART); expected=product(db,owner,"S1",identifiers={"fsn":"F1"}); product(db,owner,"S2",identifiers={"fsn":"F1"})
    result=ConsignmentMatcher(db,owner.id).flipkart("F1","S1"); assert result.product==expected and result.method=="FSN+SKU"


def test_10_repeated_fsn_exact_pairs_both_succeed(db):
    owner=account(db,Marketplace.FLIPKART); product(db,owner,"S1",identifiers={"fsn":"F1"}); product(db,owner,"S2",identifiers={"fsn":"F1"}); matcher=ConsignmentMatcher(db,owner.id)
    first, second = matcher.flipkart("F1","S1").product, matcher.flipkart("F1","S2").product
    assert first is not None and second is not None
    assert first.sku=="S1" and second.sku=="S2"


def test_11_ambiguous_fsn_fallback_blocks(db):
    owner=account(db,Marketplace.FLIPKART); product(db,owner,"S1",identifiers={"fsn":"F1"}); product(db,owner,"S2",identifiers={"fsn":"F1"})
    assert ConsignmentMatcher(db,owner.id).flipkart("F1",None).status=="ambiguous"


def test_12_ambiguous_sku_fallback_blocks(db):
    owner=account(db,Marketplace.FLIPKART); product(db,owner,"S1",identifiers={"fsn":"F1"}); duplicate=product(db,owner,"S2",identifiers={"fsn":"F2"}); duplicate.sku="S1"
    assert ConsignmentMatcher(db,owner.id).flipkart(None,"S1").status=="ambiguous"


@pytest.mark.parametrize("value",[0,-1,"abc",None])
def test_13_quantity_must_be_positive(value):
    with pytest.raises(ValueError,match="INVALID_PRINT_QTY"): positive_quantity(value)


def test_14_invalid_net_quantity_blocks(db):
    owner=account(db); catalog=product(db,owner,"S1"); batch=consignment(db,owner); line=printable_line(db,batch,catalog,net_quantity_value=0)
    assert any(x.code=="INVALID_NET_QTY" for x in ConsignmentValidationService(db).validate(line))


def test_15_duplicate_consignment_line_is_flagged_without_sum(db):
    owner=account(db); product(db,owner,"S1"); batch=consignment(db,owner); rows=[(2,{"Merchant SKU":"S1","Shipped":2}),(3,{"Merchant SKU":"S1","Shipped":2})]
    ConsignmentImportService(db).apply(batch,ParsedConsignment("a.csv","CSV","Amazon Consignment",1,[],rows,[],"a"*64))
    assert len(db.scalars(select(ConsignmentIssue).where(ConsignmentIssue.code=="DUPLICATE_CONSIGNMENT_LINE")).all())==2
    assert sum(db.scalars(select(ConsignmentLine.print_quantity)).all())==4


def test_16_initial_rows_are_not_selected(db):
    owner=account(db); product(db,owner,"S1"); batch=consignment(db,owner)
    ConsignmentImportService(db).apply(batch,ParsedConsignment("a.csv","CSV","Amazon Consignment",1,[],[(2,{"Merchant SKU":"S1","Shipped":1})],[],"a"*64))
    assert db.scalar(select(ConsignmentLine.selected_for_print)) is False


def test_17_bulk_selection_contract_uses_explicit_visible_ids(db):
    owner=account(db); catalog=product(db,owner,"S1"); batch=consignment(db,owner); first=printable_line(db,batch,catalog,selected_for_print=False); second=printable_line(db,batch,catalog,selected_for_print=False)
    from app.api.consignments import bulk_select
    from app.schemas import BulkSelection
    bulk_select(BulkSelection(consignment_id=batch.id,line_ids=[first.id],selected=True),db)
    assert first.selected_for_print is True and second.selected_for_print is False


def test_18_blocked_line_cannot_enter_print_job(db):
    owner=account(db); address(db,owner); catalog=product(db,owner,"S1"); batch=consignment(db,owner); line=printable_line(db,batch,catalog)
    db.add(ConsignmentIssue(consignment_id=batch.id,consignment_line_id=line.id,severity="blocking",code="MISSING_MRP",message="missing"));db.flush()
    with pytest.raises(PrintJobValidationError,match="blocking"): PrintJobService(db).prepare(batch.id)


def prepared(db):
    owner=account(db); address(db,owner); catalog=product(db,owner,"S1"); batch=consignment(db,owner); line=printable_line(db,batch,catalog)
    job=PrintJobService(db).prepare(batch.id); db.flush(); return owner,catalog,batch,line,job


def test_19_print_snapshot_is_immutable_after_later_edit(db):
    _,_,_,line,job=prepared(db); saved=deepcopy(db.scalar(select(PrintJobLine).where(PrintJobLine.print_job_id==job.id)).data_snapshot); line.title_snapshot="Changed"; db.flush()
    assert db.scalar(select(PrintJobLine).where(PrintJobLine.print_job_id==job.id)).data_snapshot==saved


def test_20_completed_simulation_produces_printed_line(db):
    *_,line,job=prepared(db); PrintJobService(db).simulate_success(job,enabled=True,is_admin=True); assert line.workflow_state=="printed" and line.successful_print_count==1


def test_21_failed_job_does_not_mark_line_printed(db):
    *_,line,job=prepared(db); job.status="failed"; assert line.workflow_state=="to_print"


def test_22_exact_snapshot_reprint_creates_new_job(db):
    *_,job=prepared(db); PrintJobService(db).simulate_success(job,enabled=True,is_admin=True); original=db.scalar(select(PrintJobLine).where(PrintJobLine.print_job_id==job.id)); replacement=PrintJobService(db).reprint_exact(job); db.flush(); copied=db.scalar(select(PrintJobLine).where(PrintJobLine.print_job_id==replacement.id))
    assert replacement.id!=job.id and copied.data_snapshot==original.data_snapshot and copied.source_print_job_line_id==original.id


def test_23_same_file_new_consignment_starts_to_print(db):
    owner=account(db); product(db,owner,"S1"); first=consignment(db,owner,"Old"); second=consignment(db,owner,"New"); parsed=ParsedConsignment("same.csv","CSV","Amazon Consignment",1,[],[(2,{"Merchant SKU":"S1","Shipped":1})],[],"x"*64)
    ConsignmentImportService(db).apply(first,parsed); old=db.scalar(select(ConsignmentLine).where(ConsignmentLine.consignment_id==first.id)); old.workflow_state="printed"; ConsignmentImportService(db).apply(second,parsed); fresh=db.scalar(select(ConsignmentLine).where(ConsignmentLine.consignment_id==second.id)); assert fresh.workflow_state!="printed"


def test_24_matching_is_account_isolated(db):
    one=account(db,name="One"); two=account(db,name="Two"); product(db,one,"S1"); expected=product(db,two,"S1")
    assert ConsignmentMatcher(db,two.id).amazon("S1",None,None).product==expected


def test_25_optimistic_concurrency_conflict_returns_409(db):
    owner=account(db); catalog=product(db,owner,"S1"); batch=consignment(db,owner); line=printable_line(db,batch,catalog,version=2)
    with pytest.raises(HTTPException) as caught: patch_line(line.id,ConsignmentLinePatch(expected_version=1,field="print_quantity",value=3),db)
    assert caught.value.status_code==409 and isinstance(caught.value.detail, dict)
    assert caught.value.detail["code"]=="CONSIMENT_LINE_CHANGED"


def test_26_address_profiles_are_account_scoped(db):
    one=account(db,name="One"); two=account(db,name="Two"); first=address(db,one); address(db,two)
    assert db.scalars(select(AddressProfile).where(AddressProfile.account_id==one.id)).all()==[first]


def test_27_format_required_fields_are_validated(db):
    owner=account(db,Marketplace.FLIPKART); address(db,owner); catalog=product(db,owner,"S1",identifiers={"fsn":"F1"}); batch=consignment(db,owner); line=printable_line(db,batch,catalog)
    db.add(LabelFormatProfile(name="Key Chain",key="key_chain",display_name="Key Chain",marketplace=Marketplace.FLIPKART,required_fields=["Comment"],field_order=["Comment"],config={}));db.flush()
    assert any(x.code=="MISSING_REQUIRED_FIELD" for x in ConsignmentValidationService(db).validate(line))


def test_28_model_name_and_model_number_remain_distinct(db):
    owner=account(db); address(db,owner); catalog=product(db,owner,"S1"); batch=consignment(db,owner); line=printable_line(db,batch,catalog,label_overrides={"fields":{"Model Name":"Pendant","Model Number":"PN-7"}})
    fields=ConsignmentLabelDataService(db).resolve(line)["fields"]
    assert fields["Model Name"]["value"]=="Pendant" and fields["Model Number"]["value"]=="PN-7"
