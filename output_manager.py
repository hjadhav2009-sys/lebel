from pathlib import Path
import csv
import json
import os
import re
import time
from datetime import datetime

APP_FOLDER_NAME = "MMS_Label_Tools_Output"

try:
    from marketplace_v12 import runtime_paths
except Exception:
    runtime_paths = None

def desktop_dir() -> Path:
    d = Path.home() / "Desktop"
    return d if d.exists() else Path.home()

def root_dir() -> Path:
    if runtime_paths is not None:
        try:
            return runtime_paths.output_root()
        except Exception:
            pass
    root = desktop_dir() / APP_FOLDER_NAME
    for sub in [
        "Amazon_Packing_Labels",
        "Marketplace_Product_Labels",
        "Marketplace_Product_PRN",
        "Flipkart_Amazon_Cropped_Labels",
        "Database",
        "Database/amazon_packing",
        "Database/marketplace_v12",
        "Database/output_records",
        "Logs",
        "Raw_Uploads",
        "Raw_Uploads/Amazon_Packing_Labels",
        "Raw_Uploads/Marketplace_Product_Labels",
        "Raw_Uploads/Flipkart_Amazon_Cropped_Labels",
        "Temp",
    ]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root

def subdir(name: str) -> Path:
    p = root_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p

def safe_text(value: str, fallback: str = "Output") -> str:
    value = str(value or "").strip()
    value = re.sub(r"[^A-Za-z0-9._ -]+", "_", value)
    value = re.sub(r"\s+", "_", value).strip("._- ")
    return (value or fallback)[:70]

def dated_name(prefix: str, custom_name: str = "", purpose: str = "", source_name: str = "", ext: str = ".pdf") -> str:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    parts = [safe_text(prefix, "Output")]
    if purpose:
        parts.append(safe_text(purpose, "Purpose"))
    if custom_name:
        parts.append(safe_text(custom_name, "Name"))
    if source_name:
        parts.append(safe_text(Path(source_name).stem, "Source"))
    parts.append(stamp)
    if not ext.startswith('.'):
        ext = '.' + ext
    return "_".join(parts) + ext

def output_path(folder: str, prefix: str, custom_name: str = "", purpose: str = "", source_name: str = "", ext: str = ".pdf") -> Path:
    p = subdir(folder) / dated_name(prefix, custom_name, purpose, source_name, ext)
    # avoid collision
    if not p.exists():
        return p
    n=2
    while True:
        candidate = p.with_name(p.stem + f"_{n}" + p.suffix)
        if not candidate.exists():
            return candidate
        n += 1

def dated_pdf_path(folder: str, prefix: str, source_name: str = "") -> Path:
    return output_path(folder, prefix, source_name=source_name, ext=".pdf")

def record_output(tool: str, output_file, purpose: str = "", custom_name: str = "", input_files=None, notes: str = ""):
    root = root_dir()
    rec_dir = root / "Database" / "output_records"
    rec_dir.mkdir(parents=True, exist_ok=True)
    input_files = input_files or []
    if isinstance(input_files, (str, Path)):
        input_files = [str(input_files)]
    row = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tool": tool,
        "purpose": purpose,
        "custom_name": custom_name,
        "output_file": str(output_file),
        "input_files": " | ".join(map(str, input_files)),
        "notes": notes,
    }
    csv_path = rec_dir / "output_history.csv"
    write_header = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            w.writeheader()
        w.writerow(row)
    json_path = rec_dir / "output_history.jsonl"
    with open(json_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return csv_path
