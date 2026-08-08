from io import BytesIO

from openpyxl import Workbook

from app.services.file_reader import file_fingerprint, parse_catalog


def workbook_bytes(setup):
    workbook = Workbook()
    setup(workbook)
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def test_multi_sheet_detection_chooses_supported_sheet():
    def setup(workbook):
        workbook.active.title = "Instructions"
        workbook.active.append(["Read me", "Nothing to import"])
        data = workbook.create_sheet("Unexpected Name")
        data.append(["Listing Id", "FSN", "SKU", "MRP", "brand"])
        data.append(["L1", "FSN1", "SKU1", 799, "MMS"])
    parsed = parse_catalog("catalog.xlsx", workbook_bytes(setup), "flipkart")
    assert parsed.sheet_name == "Unexpected Name"
    assert len(parsed.rows) == 1


def test_formula_without_cached_result_is_reported_and_not_imported():
    def setup(workbook):
        sheet = workbook.active
        sheet.append(["Listing Id", "FSN", "SKU", "MRP", "brand"])
        sheet.append(["L1", "FSN1", "SKU1", "=700+99", "MMS"])
    parsed = parse_catalog("formula.xlsx", workbook_bytes(setup), "flipkart")
    assert any("FORMULA_RESULT_MISSING" in warning for warning in parsed.warnings)
    assert parsed.rows == []


def test_file_fingerprint_is_stable_and_content_sensitive():
    assert file_fingerprint(b"same") == file_fingerprint(b"same")
    assert file_fingerprint(b"same") != file_fingerprint(b"different")
