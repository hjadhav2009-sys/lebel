from app.services.normalization import NormalizedProduct, classify_snapshots, detect_header_row, flipkart_product_url, normalize_row


SKU_KEY = "contribution_sku#1.value"
ASIN_KEY = "amzn1.volt.ca.product_id_value"
MRP_KEY = "purchasable_offer[marketplace_id=A21TJRUUN4KGV][audience=ALL]#1.maximum_retail_price#1.schedule#1.value_with_tax"
IMAGE_KEY = "main_product_image_locator[marketplace_id=A21TJRUUN4KGV]#1.media_location"


def test_amazon_technical_header_detection():
    rows = [["instructions", None], ["SKU", "Product ID", "Maximum Retail Price"], [SKU_KEY, ASIN_KEY, MRP_KEY]]
    assert detect_header_row(rows, "amazon") == 2


def test_amazon_alias_fallback():
    row = normalize_row(["SKU", "ASIN", "Maximum Retail Price", "Main Image URL"], ["ABC-1", "B0123", "799", "https://images/x.jpg"], "amazon")
    assert row.sku == "ABC-1" and row.identifiers["asin"] == "B0123"
    assert row.mrp == "799.00" and row.images == ["https://images/x.jpg"]


def test_three_amazon_template_variants_ignore_column_position():
    variants = [
        ([SKU_KEY, ASIN_KEY, MRP_KEY, IMAGE_KEY], ["A", "ASIN-A", 499, "https://i/a.jpg"]),
        ([MRP_KEY, IMAGE_KEY, SKU_KEY, ASIN_KEY], [599, "https://i/b.jpg", "B", "ASIN-B"]),
        ([ASIN_KEY, SKU_KEY, IMAGE_KEY, MRP_KEY], ["ASIN-C", "C", "https://i/c.jpg", 699]),
    ]
    for headers, values in variants:
        row = normalize_row(headers, values, "amazon")
        assert row.sku in {"A", "B", "C"} and row.mrp in {"499.00", "599.00", "699.00"}


def test_flipkart_normalized_import_and_url():
    row = normalize_row(["Listing Id", "FSN", "SKU", "MRP", "FSP", "brand", "color"], ["L1", "FSN1", "SKU1", "999", "499", "MMS", "Gold"], "flipkart", source_category="key_chain")
    assert row.identifiers == {"fsn": "FSN1", "listing_id": "L1"}
    assert row.extra_attributes["color"] == "Gold"
    assert flipkart_product_url("FSN1").endswith("pid=FSN1")


def test_stable_business_keys_and_unchanged_hash():
    first = NormalizedProduct("amazon", " SKU-1 ", mrp="799.00")
    second = NormalizedProduct("amazon", "sku-1", mrp="799.00")
    assert first.business_key() == second.business_key()
    assert first.row_hash() != second.row_hash()  # source values remain auditable


def test_changed_row_update_classification():
    old = NormalizedProduct("amazon", "A", mrp="700.00")
    changed = NormalizedProduct("amazon", "A", mrp="799.00")
    result = classify_snapshots({old.business_key(): old.row_hash()}, [changed])
    assert result["updated"] == 1


def test_incremental_20000_to_20200_scenario():
    old_rows = [NormalizedProduct("flipkart", f"SKU-{i}", mrp="799.00", identifiers={"fsn": f"FSN-{i}"}) for i in range(20_000)]
    existing = {row.business_key(): row.row_hash() for row in old_rows}
    incoming = old_rows + [NormalizedProduct("flipkart", f"SKU-{i}", mrp="799.00", identifiers={"fsn": f"FSN-{i}"}) for i in range(20_000, 20_200)]
    result = classify_snapshots(existing, incoming)
    assert result == {"new": 200, "updated": 0, "unchanged": 20_000, "errors": 0}


def test_duplicate_identifier_blocks_second_row():
    rows = [NormalizedProduct("flipkart", "A", identifiers={"fsn": "SAME"}), NormalizedProduct("flipkart", "B", identifiers={"fsn": "SAME"})]
    assert classify_snapshots({}, rows)["errors"] == 1


def test_missing_mrp_never_defaults_to_799():
    row = normalize_row(["SKU", "MRP"], ["A", ""], "flipkart")
    assert row.mrp is None
