# -*- mode: python ; coding: utf-8 -*-

import json
from pathlib import Path


datas = []
default_data_dir = Path("build") / "pyinstaller_default_data"
default_data_dir.mkdir(parents=True, exist_ok=True)
default_mapping_path = default_data_dir / "amazon_mapping_settings.json"
default_mapping_path.write_text(
    json.dumps(
        {
            "selected_branch": "",
            "last_master_path": "",
            "consignment": {
                "merchant_sku": "Merchant SKU",
                "title": "Title",
                "asin": "ASIN",
                "fnsku": "FNSKU",
                "shipped_qty": "Shipped",
                "condition": "Condition",
            },
            "master": {
                "item_name": "item-name",
                "item_description": "item-description",
                "seller_sku": "seller-sku",
                "asin": "asin1",
                "product_id": "product-id",
                "mrp": "maximum-retail-price",
            },
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
for path in Path("data").glob("*.json"):
    if path.name != "amazon_mapping_settings.json":
        datas.append((str(path), "data"))
datas.append((str(default_mapping_path), "data"))

for path in Path("reference_templates").glob("*"):
    if path.is_file():
        datas.append((str(path), "reference_templates"))

hiddenimports = [
    "pandas",
    "openpyxl",
    "reportlab",
    "PIL",
    "win32api",
    "win32print",
]

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MarketplaceLabelGenerator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MarketplaceLabelGenerator",
)
