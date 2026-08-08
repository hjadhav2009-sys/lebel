from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import CatalogImport, CatalogProduct, Marketplace, MarketplaceAccount, RowAction, CatalogImportRow
from app.services.import_service import CatalogImportService
from app.services.normalization import NormalizedProduct


def make_import(session, account, suffix):
    item = CatalogImport(account_id=account.id, source_file="amazon.xlsx", original_filename="amazon.xlsx", sheet_name="Data", file_sha256=suffix * 64, file_size=100, detected_type="Amazon Listing Template")
    session.add(item); session.flush(); return item


def test_changed_images_and_identifiers_persist_then_reimport_is_unchanged():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        account = MarketplaceAccount(marketplace=Marketplace.AMAZON, name="Mumbai")
        session.add(account); session.flush()
        first = NormalizedProduct("amazon", "SKU-1", identifiers={"asin":"OLD"}, images=["https://img/old.jpg"], source_template="template-a")
        CatalogImportService(session).apply(make_import(session, account, "a"), [(2, {"SKU":"SKU-1"}, first)])
        changed = NormalizedProduct("amazon", "SKU-1", identifiers={"asin":"NEW","fnsku":"X001"}, images=["https://img/new.jpg"], source_template="template-a")
        CatalogImportService(session).apply(make_import(session, account, "b"), [(2, {"SKU":"SKU-1"}, changed)])
        product = session.scalar(select(CatalogProduct))
        assert product is not None
        assert {(i.kind, i.value) for i in product.identifiers} >= {("asin","NEW"),("fnsku","X001")}
        assert any(image.url == "https://img/new.jpg" and image.status == "available" for image in product.images)
        third = make_import(session, account, "c")
        CatalogImportService(session).apply(third, [(2, {"SKU":"SKU-1"}, changed)])
        action = session.scalar(select(CatalogImportRow.action).where(CatalogImportRow.import_id == third.id))
        assert action == RowAction.UNCHANGED


def test_multiple_amazon_templates_enrich_without_deleting_images():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        account = MarketplaceAccount(marketplace=Marketplace.AMAZON, name="Mumbai")
        session.add(account); session.flush()
        one = NormalizedProduct("amazon", "SKU-1", images=["https://img/a.jpg"], source_template="template-a")
        two = NormalizedProduct("amazon", "SKU-1", images=["https://img/b.jpg"], source_template="template-b")
        CatalogImportService(session).apply(make_import(session, account, "d"), [(2, {}, one)])
        CatalogImportService(session).apply(make_import(session, account, "e"), [(2, {}, two)])
        product = session.scalar(select(CatalogProduct))
        assert product is not None
        assert {image.url for image in product.images} == {"https://img/a.jpg", "https://img/b.jpg"}
