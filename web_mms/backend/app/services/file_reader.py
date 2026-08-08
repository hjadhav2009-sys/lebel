import csv
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from app.services.normalization import NormalizedProduct, detect_header_row, normalize_row


@dataclass(slots=True)
class ParsedCatalog:
    detected_type: str
    header_row: int
    headers: list[Any]
    rows: list[tuple[int, dict, NormalizedProduct]]


def _matrix(filename: str, payload: bytes) -> list[list[Any]]:
    suffix = Path(filename).suffix.casefold()
    if suffix == ".csv":
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = payload.decode("cp1252")
        return [list(row) for row in csv.reader(StringIO(text))]
    if suffix in {".xlsx", ".xlsm"}:
        workbook = load_workbook(BytesIO(payload), read_only=True, data_only=True, keep_vba=False)
        sheet = workbook[workbook.sheetnames[0]]
        rows = [list(row) for row in sheet.iter_rows(values_only=True)]
        workbook.close()
        return rows
    raise ValueError("Only CSV, XLSX, and XLSM files are supported")


def parse_catalog(filename: str, payload: bytes, marketplace: str, source_category: str | None = None) -> ParsedCatalog:
    matrix = _matrix(filename, payload)
    header_index = detect_header_row(matrix, marketplace)
    headers = matrix[header_index]
    parsed = []
    template = Path(filename).stem
    for source_index, values in enumerate(matrix[header_index + 1 :], start=header_index + 2):
        if not any(value is not None and str(value).strip() for value in values):
            continue
        raw = {str(headers[index] or f"column_{index + 1}"): value for index, value in enumerate(values) if index < len(headers)}
        parsed.append((source_index, raw, normalize_row(headers, values, marketplace, source_template=template, source_category=source_category)))
    detected = "Amazon Listing Template" if marketplace == "amazon" else "Flipkart QC Catalog"
    return ParsedCatalog(detected, header_index + 1, headers, parsed)
