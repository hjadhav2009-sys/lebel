import os
import sys
import json
import time
import traceback
import subprocess
import threading
import copy
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

import amazon_label_renderer
import amazon_prn_renderer
import amazon_reader
import amazon_rules
import amazon_validation

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.lib.units import mm
    from reportlab.graphics.barcode import code128
except Exception:
    pdfcanvas = None
    mm = 2.834645669291339
    code128 = None

APP_VERSION = "V16 Advanced"
APP_NAME = f"M Men Style - Marketplace Label Generator {APP_VERSION}"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "outputs"
LOG_DIR = BASE_DIR / "logs"
SAMPLE_DIR = BASE_DIR / "samples"
for d in (DATA_DIR, OUT_DIR, LOG_DIR, SAMPLE_DIR):
    d.mkdir(exist_ok=True)
SETTINGS_FILE = DATA_DIR / "branches.json"
FORMATS_FILE = DATA_DIR / "label_formats.json"
LOG_FILE = LOG_DIR / "debug_log.txt"
CURRENT_AMAZON_MASTER_FILE = DATA_DIR / "current_amazon_master.xlsx"

DEFAULT_BRANCHES = {
    "Mumbai Branch": {
        "name": "Mumbai Branch",
        "marketed_by": "Sujal Fashion Works, Shop No F-10,",
        "address": "Amranate, Sec-09E, Kalamboli. Navi Mumbai",
        "email": "Sujalfashionworks@gmail.com",
        "phone": "+91-9594790929",
        "origin": "Country of Origin: India",
        "month_year": "May 2026",
        "barcode_column": "FSN",
        "dimension": "85mm*70mm*8mm",
        "roll_page_width_mm": "106.0",
        "roll_label_width_mm": "50.0",
        "roll_label_height_mm": "50.0",
        "roll_gap_x_mm": "3.0",
        "roll_margin_x_mm": "1.5",
        "roll_margin_y_mm": "0.0",
        "roll_rows_per_page": "1"
    }
}

FORMATS = {
    "key_chain": {
        "title": "Key Chain", "generic": "Key Chain",
        "fields": [("Comment", ["comment"]), ("Color", ["color"]), ("Model Number", ["model_number", "model no", "model"]), ("Brand", ["brand"])]
    },
    "pendant_locket": {
        "title": "Pendant Locket", "generic": "Pendant Locket",
        "fields": [("Body Material", ["body_material", "material"]), ("Plating", ["plating"]), ("Brand Color", ["brand_color", "color"]), ("Model Number", ["model_number", "model no", "model"]), ("Brand", ["brand"])]
    },
    "bangle_bracelet_armlet": {
        "title": "Bangle Bracelet Armlet", "generic": "Bracelet",
        "fields": [("Bangle Size", ["bangle_size", "size"]), ("Diameter", ["diameter"]), ("Color", ["color"]), ("Pack Of", ["pack_of", "pack of"]), ("Model Number", ["model_number", "model no", "model"]), ("Brand", ["brand"])]
    },
    "earring": {
        "title": "Earring", "generic": "Earring",
        "fields": [("Sales Package", ["sales_package", "sales package"]), ("Color", ["color"]), ("Model Number", ["model_number", "model no", "model"]), ("Type", ["type"]), ("Brand", ["brand"])]
    },
    "jewellery_set": {
        "title": "Jewellery Set", "generic": "Jewellery Set",
        "fields": [("Sales Package", ["sales_package_id", "sales_package", "sales package"]), ("Color", ["color"]), ("Model Number", ["model_number", "model no", "model"]), ("Brand", ["brand"])]
    },
    "ring": {
        "title": "Ring", "generic": "Ring",
        "fields": [("Color", ["color"]), ("Size", ["ring_size", "size"]), ("Model Number", ["model_number", "model no", "model"]), ("Brand", ["brand"])]
    },
    "necklace_chain": {
        "title": "Necklace Chain", "generic": "Necklace Chain",
        "fields": [("Color", ["color"]), ("Model Number", ["model_number", "model no", "model"]), ("Brand", ["brand"])]
    },
    "car_hanger": {
        "title": "Car Hanger", "generic": "Car Hanger",
        "fields": [("Color", ["color"]), ("Model Number", ["model_number", "model no", "model"]), ("Brand", ["brand"])]
    },
}


def save_formats(data):
    DATA_DIR.mkdir(exist_ok=True)
    serializable = {}
    for k, v in data.items():
        serializable[k] = {"title": v.get("title", k), "generic": v.get("generic", ""), "fields": v.get("fields", [])}
    FORMATS_FILE.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def load_formats():
    global FORMATS
    try:
        if FORMATS_FILE.exists():
            data = json.loads(FORMATS_FILE.read_text(encoding="utf-8"))
            if data:
                FORMATS = data
                return
    except Exception:
        log(traceback.format_exc())
    save_formats(FORMATS)



def log(msg):
    try:
        LOG_DIR.mkdir(exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " | " + str(msg) + "\n")
    except Exception:
        pass


load_formats()

def clean_val(v):
    if v is None:
        return ""
    try:
        if pd is not None and pd.isna(v):
            return ""
    except Exception:
        pass
    s = str(v).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return s


def safe_int(v, default=1):
    try:
        n = int(float(str(v).strip()))
        return n if n > 0 else default
    except Exception:
        return default

def safe_float(v, default):
    try:
        return float(str(v).strip())
    except Exception:
        return default

def norm_col(c):
    return str(c).strip().lower().replace(" ", "_").replace("-", "_")


def find_col(df, aliases):
    norm = {norm_col(c): c for c in df.columns}
    for alias in aliases:
        key = norm_col(alias)
        if key in norm:
            return norm[key]
    for key, original in norm.items():
        for alias in aliases:
            if norm_col(alias) in key:
                return original
    return None


def row_value(df, row, aliases, default=""):
    col = find_col(df, aliases)
    if col is None:
        return default
    return clean_val(row.get(col, default))


def read_file(path):
    if pd is None:
        raise RuntimeError("pandas is not installed. Run install_requirements.bat first.")
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        last_err = None
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
            try:
                return pd.read_csv(path, dtype=str, encoding=enc).fillna("")
            except Exception as e:
                last_err = e
        raise last_err
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str).fillna("")
    raise RuntimeError("Only CSV/XLSX/XLS files are supported.")


def detect_format(path, df):
    name = Path(path).name.lower().replace(" ", "_")
    if "bangle" in name or "bracelet" in name or "armlet" in name:
        return "bangle_bracelet_armlet"
    if "earring" in name:
        return "earring"
    if "jewellery" in name or "jewelry" in name or "set" in name:
        return "jewellery_set"
    if "pendant" in name or "locket" in name:
        return "pendant_locket"
    if "necklace" in name:
        return "necklace_chain"
    if "hanger" in name or "hanging" in name:
        return "car_hanger"
    if "ring" in name:
        return "ring"
    if "key" in name or "keychain" in name:
        return "key_chain"
    cols = [norm_col(c) for c in df.columns]
    if "bangle_size" in cols or "diameter" in cols:
        return "bangle_bracelet_armlet"
    if "sales_package" in cols and "type" in cols:
        return "earring"
    if "body_material" in cols or "plating" in cols:
        return "pendant_locket"
    return "key_chain"


def wrap_text(text, max_chars):
    text = clean_val(text)
    if not text:
        return [""]
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def load_branches():
    try:
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if data:
                base_defaults = DEFAULT_BRANCHES["Mumbai Branch"]
                changed = False
                for b in data.values():
                    for k, v in base_defaults.items():
                        if k not in b:
                            b[k] = v
                            changed = True
                if changed:
                    save_branches(data)
                return data
    except Exception:
        log(traceback.format_exc())
    save_branches(DEFAULT_BRANCHES)
    return json.loads(json.dumps(DEFAULT_BRANCHES))


def save_branches(data):
    DATA_DIR.mkdir(exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_label_text(fmt_key, df, row, branch):
    cfg = FORMATS.get(fmt_key, FORMATS["key_chain"])
    top_lines = []
    for label, aliases in cfg["fields"]:
        value = row_value(df, row, aliases, "")
        if value:
            top_lines.append(f"{label}: {value}")
    top_lines.append("Net Quantity: 1 N")
    top_lines.append(f"Dimensions: {branch.get('dimension', '85mm*70mm*8mm')}")
    mrp = row_value(df, row, ["MRP", "mrp"], "")
    top_lines.append(f"MRP Rs.{mrp}.00 Inclusive of all taxes" if mrp else "MRP Rs. Inclusive of all taxes")
    top_lines.append(f"Generic Name: {cfg.get('generic', '')}")
    top_lines.append(f"Month & Year of Manufacturing: {branch.get('month_year', '')}")
    lower = [
        "Manufactured by / Marketed by:",
        branch.get("marketed_by", ""),
        branch.get("address", ""),
        f"Email: {branch.get('email','')}",
    ]
    if branch.get("phone"):
        lower.append(f"Contact: {branch.get('phone')}")
    if branch.get("origin"):
        lower.append(branch.get("origin"))
    return cfg["title"], top_lines, lower


def get_barcode_value(df, row, branch):
    pref = branch.get("barcode_column", "FSN")
    return row_value(df, row, [pref, "FSN", "EAN", "LID", "Listing Id", "listing_id"], "NO-BARCODE") or "NO-BARCODE"

def detect_qty(df, row):
    return safe_int(row_value(df, row, ["print_qty", "label_qty", "quantity", "qty", "consignment_qty", "consignment quantity"], "1"), 1)

def get_row_qty(item, row_index):
    try:
        return safe_int(item.get("qty", {}).get(int(row_index), 1), 1)
    except Exception:
        return 1


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1450x850")
        self.minsize(1100, 700)
        self.branches = load_branches()
        self.files = []
        self.amazon_workbook = None
        self.amazon_master = None
        self.amazon_consignment = None
        self.amazon_master_df = None
        self.amazon_consignment_df = None
        self.amazon_master_path = ""
        self.amazon_consignment_path = ""
        self.amazon_rows = []
        self.amazon_manual_mrp = {}
        self.amazon_qty_overrides = {}
        self.amazon_mapping = amazon_rules.load_mapping_settings()
        self.amazon_category_rules = amazon_rules.load_category_rules()
        self.amazon_brand_rules = amazon_rules.load_brand_rules()
        self.amazon_last_report = ""
        self.last_prn = ""
        self.last_pdf = ""
        self.status_var = tk.StringVar(value="Ready")
        self.row_qty_var = tk.StringVar(value="1")
        self.amazon_qty_var = tk.StringVar(value="1")
        self.change_format_var = tk.StringVar()
        self.build_ui()
        self.refresh_branches()
        self.show_empty_preview()
        self.try_auto_load_amazon_master()
        log("App started")

    def build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        nb = ttk.Notebook(self)
        self.main_notebook = nb
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_gen = ttk.Frame(nb)
        self.tab_amazon = ttk.Frame(nb)
        self.tab_set = ttk.Frame(nb)
        self.tab_map = ttk.Frame(nb)
        nb.add(self.tab_gen, text="Flipkart Labels")
        nb.add(self.tab_amazon, text="Amazon Labels")
        nb.add(self.tab_set, text="Branch / Address Settings")
        nb.add(self.tab_map, text="Format / Mapping Settings")

        toolbar = ttk.Frame(self.tab_gen)
        toolbar.pack(fill="x", padx=4, pady=4)
        ttk.Button(toolbar, text="Upload Files", command=self.upload_files).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Clear", command=self.clear_files).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Preview Selected", command=self.preview_selected).pack(side="left", padx=12)
        ttk.Button(toolbar, text="Validate All", command=self.validate_all).pack(side="left", padx=4)
        self.generate_btn = ttk.Button(toolbar, text="Generate PDF", command=self.generate_pdf_clicked)
        self.generate_btn.pack(side="left", padx=4)
        ttk.Button(toolbar, text="Open Last PDF", command=self.open_last_pdf).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Print Last PDF", command=self.print_last_pdf).pack(side="left", padx=4)
        ttk.Label(toolbar, text="Branch:").pack(side="left", padx=(18, 4))
        self.branch_var = tk.StringVar()
        self.branch_combo = ttk.Combobox(toolbar, textvariable=self.branch_var, state="readonly", width=22)
        self.branch_combo.pack(side="left")
        ttk.Label(toolbar, text="PDF Layout:").pack(side="left", padx=(18, 4))
        self.layout_var = tk.StringVar(value="2-column sticker roll")
        self.layout_combo = ttk.Combobox(toolbar, textvariable=self.layout_var, state="readonly", width=24, values=["Single label pages", "2-column sticker roll"])
        self.layout_combo.pack(side="left")
        ttk.Label(toolbar, text="Change selected format:").pack(side="left", padx=(18, 4))
        self.change_format_combo = ttk.Combobox(toolbar, textvariable=self.change_format_var, state="readonly", width=22)
        self.change_format_combo.pack(side="left")
        ttk.Button(toolbar, text="Apply", command=self.apply_selected_format).pack(side="left", padx=4)

        body = ttk.Panedwindow(self.tab_gen, orient="horizontal")
        body.pack(fill="both", expand=True, padx=4, pady=4)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=1)

        ttk.Label(left, text="Uploaded Flipkart Files").pack(anchor="w")
        self.file_tree = ttk.Treeview(left, columns=("file", "format", "rows"), show="headings", height=8)
        for col, w in [("file", 390), ("format", 220), ("rows", 80)]:
            self.file_tree.heading(col, text=col.title())
            self.file_tree.column(col, width=w, anchor="w")
        self.file_tree.pack(fill="x", pady=(3, 12))
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select_light)

        ttk.Label(left, text="Selected File Data Preview").pack(anchor="w")
        self.data_tree = ttk.Treeview(left, show="headings", height=18)
        self.data_tree.pack(fill="both", expand=True, pady=(3, 0))
        self.data_tree.bind("<<TreeviewSelect>>", self.on_data_row_select)
        self.data_tree.bind("<Double-1>", self.on_data_tree_double_click)
        qtybar = ttk.Frame(left)
        qtybar.pack(fill="x", pady=6)
        ttk.Label(qtybar, text="Print Qty for selected SKU (PDF repeats label this many times):").pack(side="left")
        ttk.Entry(qtybar, textvariable=self.row_qty_var, width=8).pack(side="left", padx=5)
        ttk.Button(qtybar, text="Apply Qty to Selected SKU", command=self.apply_row_qty).pack(side="left", padx=4)
        ttk.Button(qtybar, text="Set Selected Qty Popup", command=self.quick_set_selected_qty).pack(side="left", padx=4)
        ttk.Button(qtybar, text="Edit All Quantities", command=self.edit_quantities_dialog).pack(side="left", padx=4)
        ttk.Button(qtybar, text="Apply Qty to All Rows", command=self.apply_qty_to_all_rows).pack(side="left", padx=4)
        ttk.Button(qtybar, text="Set All Rows Qty = 1", command=self.set_all_qty_one).pack(side="left", padx=4)

        ttk.Label(right, text="Large Label Preview — click Preview Selected after choosing file").pack(anchor="w")
        self.preview = tk.Canvas(right, bg="#f4f4f4", highlightthickness=1, highlightbackground="#cccccc")
        self.preview.pack(fill="both", expand=True, padx=6, pady=6)
        self.preview.bind("<Configure>", lambda e: None)

        footer = ttk.Frame(self.tab_gen)
        footer.pack(fill="x", padx=4, pady=4)
        ttk.Label(footer, textvariable=self.status_var).pack(side="left")
        ttk.Label(footer, text="Print rule: V12 2UP roll = PDF 106mm x 50mm, gap 3mm. Print Actual Size / 100% / No Scaling.").pack(side="right")
        self.build_amazon_tab()
        self.build_settings_tab()
        self.build_format_tab()

    def build_amazon_tab(self):
        toolbar = ttk.Frame(self.tab_amazon)
        toolbar.pack(fill="x", padx=6, pady=4)

        def step_row(label):
            row = ttk.Frame(toolbar)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label, width=12).pack(side="left", padx=(0, 4))
            return row

        def step_button(parent, text, command, width=24):
            btn = ttk.Button(parent, text=text, command=command, width=width)
            btn.pack(side="left", padx=3, pady=1)
            return btn

        files_row = step_row("1) Files:")
        step_button(files_row, "Upload Weekly Master Listing", self.upload_amazon_master_file, width=26)
        step_button(files_row, "Upload Amazon Consignment File", self.upload_amazon_consignment_file, width=28)
        step_button(files_row, "Clear Amazon Consignment", self.clear_amazon_consignment, width=25)
        step_button(files_row, "Clear Master Listing", self.clear_amazon_master, width=22)

        check_row = step_row("2) Check:")
        step_button(check_row, "Preview Selected", self.preview_selected_amazon, width=22)
        step_button(check_row, "Validate Amazon", self.validate_amazon_clicked, width=22)
        step_button(check_row, "Fix Blocking Rows", self.fix_amazon_blockers_dialog, width=22)

        output_row = step_row("3) Output:")
        self.amazon_generate_btn = step_button(output_row, "Generate Amazon PDF", self.generate_amazon_pdf_clicked, width=22)
        self.amazon_prn_btn = step_button(output_row, "Generate Amazon PRN", self.generate_amazon_prn_clicked, width=22)
        self.amazon_prn_print_btn = step_button(output_row, "Generate PRN & Print", self.generate_amazon_prn_and_print_clicked, width=22)
        step_button(output_row, "Open Last PDF", self.open_last_pdf, width=18)
        step_button(output_row, "Open Last PRN", self.open_last_prn, width=18)
        step_button(output_row, "Print Last PDF", self.print_last_pdf, width=18)
        step_button(output_row, "Print Last PRN Direct", self.print_last_prn_direct, width=22)

        branch_row = step_row("4) Branch:")
        self.amazon_branch_var = tk.StringVar(value=self.amazon_mapping.get("selected_branch", ""))
        self.amazon_branch_combo = ttk.Combobox(branch_row, textvariable=self.amazon_branch_var, state="readonly", width=28)
        self.amazon_branch_combo.pack(side="left", padx=3)
        self.amazon_branch_combo.bind("<<ComboboxSelected>>", lambda e: self.save_amazon_selected_branch())
        ttk.Label(branch_row, text="Amazon Output Layout: BarTender 2UP 101.5x50 PRN style").pack(side="left", padx=12)

        status_box = ttk.Frame(self.tab_amazon)
        status_box.pack(fill="x", padx=8, pady=(0, 4))
        self.amazon_master_status_var = tk.StringVar(value="Master Listing: not loaded")
        self.amazon_consignment_status_var = tk.StringVar(value="Consignment File: not loaded")
        ttk.Label(status_box, textvariable=self.amazon_master_status_var).pack(anchor="w")
        ttk.Label(status_box, textvariable=self.amazon_consignment_status_var).pack(anchor="w")

        body = ttk.Panedwindow(self.tab_amazon, orient="horizontal")
        body.pack(fill="both", expand=True, padx=4, pady=4)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)

        ttk.Label(left, text="Amazon Validation").pack(anchor="w")
        table_frame = ttk.Frame(left)
        table_frame.pack(fill="both", expand=True, pady=(3, 0))
        self.amazon_tree_cols = ("status", "sku", "asin", "fnsku", "title", "heading", "brand", "mrp", "qty", "error")
        self.amazon_tree = ttk.Treeview(table_frame, columns=self.amazon_tree_cols, show="headings", height=22)
        headings = {
            "status": "Status",
            "sku": "SKU",
            "asin": "ASIN",
            "fnsku": "FNSKU",
            "title": "Title",
            "heading": "Main Heading",
            "brand": "Brand",
            "mrp": "MRP",
            "qty": "Print Qty",
            "error": "Error message",
        }
        widths = {
            "status": 70,
            "sku": 135,
            "asin": 105,
            "fnsku": 125,
            "title": 260,
            "heading": 135,
            "brand": 110,
            "mrp": 80,
            "qty": 80,
            "error": 260,
        }
        for col in self.amazon_tree_cols:
            self.amazon_tree.heading(col, text=headings[col])
            self.amazon_tree.column(col, width=widths[col], anchor="w", stretch=True)
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.amazon_tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.amazon_tree.xview)
        self.amazon_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.amazon_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.amazon_tree.bind("<<TreeviewSelect>>", self.on_amazon_row_select)
        self.amazon_tree.bind("<Double-1>", self.quick_set_amazon_qty)

        qtybar = ttk.Frame(left)
        qtybar.pack(fill="x", pady=6)
        ttk.Label(qtybar, text="Print Qty for selected Amazon SKU:").pack(side="left")
        ttk.Entry(qtybar, textvariable=self.amazon_qty_var, width=8).pack(side="left", padx=5)
        ttk.Button(qtybar, text="Apply Qty to Selected SKU", command=self.apply_amazon_row_qty).pack(side="left", padx=4)
        ttk.Button(qtybar, text="Apply Qty to All Rows", command=self.apply_amazon_qty_to_all_rows).pack(side="left", padx=4)
        ttk.Button(qtybar, text="Reset Qty from Shipped", command=self.reset_amazon_qty_from_shipped).pack(side="left", padx=4)

        ttk.Label(right, text="Amazon Label Preview").pack(anchor="w")
        self.amazon_preview = tk.Canvas(right, bg="#f4f4f4", highlightthickness=1, highlightbackground="#cccccc")
        self.amazon_preview.pack(fill="both", expand=True, padx=6, pady=6)

    def build_settings_tab(self):
        top = ttk.Frame(self.tab_set)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="Branch:").pack(side="left")
        self.settings_branch_var = tk.StringVar()
        self.settings_branch_combo = ttk.Combobox(top, textvariable=self.settings_branch_var, state="readonly", width=30)
        self.settings_branch_combo.pack(side="left", padx=5)
        self.settings_branch_combo.bind("<<ComboboxSelected>>", lambda e: self.load_branch_form())
        ttk.Button(top, text="Add New Branch", command=self.add_branch).pack(side="left", padx=5)
        ttk.Button(top, text="Save Branch Settings", command=self.save_branch_form).pack(side="left", padx=5)
        ttk.Button(top, text="Delete Branch", command=self.delete_branch).pack(side="left", padx=5)

        form = ttk.Frame(self.tab_set)
        form.pack(fill="x", padx=8, pady=8)
        self.entry = {}
        rows = [
            ("name", "Branch Name"),
            ("marketed_by", "Manufactured by / Marketed by"),
            ("address", "Manufacturer / Branch Address"),
            ("email", "Email"),
            ("phone", "Phone"),
            ("origin", "Country Origin Text"),
            ("month_year", "Month & Year of Manufacturing"),
            ("barcode_column", "Barcode Column"),
            ("dimension", "Default Packaging Dimension"),
            ("roll_page_width_mm", "2UP Roll Total Width mm"),
            ("roll_label_width_mm", "2UP Label Width mm"),
            ("roll_label_height_mm", "2UP Label Height mm"),
            ("roll_gap_x_mm", "2UP Middle Gap mm"),
            ("roll_margin_x_mm", "2UP Auto/Side Margin mm"),
            ("roll_margin_y_mm", "2UP Top/Bottom Margin mm"),
            ("roll_rows_per_page", "2UP Rows per PDF Page"),
        ]
        for i, (key, label) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=5)
            ent = ttk.Entry(form, width=115)
            ent.grid(row=i, column=1, sticky="ew", padx=5, pady=5)
            self.entry[key] = ent
        form.columnconfigure(1, weight=1)
        ttk.Label(self.tab_set, text="Customer Care removed. This branch block is fixed for all labels from this branch.").pack(anchor="w", padx=14, pady=8)

    def build_format_tab(self):
        settings_nb = ttk.Notebook(self.tab_map)
        settings_nb.pack(fill="both", expand=True, padx=6, pady=6)
        self.flipkart_map_frame = ttk.Frame(settings_nb)
        self.amazon_map_frame = ttk.Frame(settings_nb)
        settings_nb.add(self.flipkart_map_frame, text="Flipkart Formats")
        settings_nb.add(self.amazon_map_frame, text="Amazon Settings")

        top = ttk.Frame(self.flipkart_map_frame)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="Format:").pack(side="left")
        self.map_format_var = tk.StringVar()
        self.map_format_combo = ttk.Combobox(top, textvariable=self.map_format_var, state="readonly", width=28)
        self.map_format_combo.pack(side="left", padx=5)
        self.map_format_combo.bind("<<ComboboxSelected>>", lambda e: self.load_format_form())
        ttk.Button(top, text="Add New Format", command=self.add_format).pack(side="left", padx=5)
        ttk.Button(top, text="Save Format Mapping", command=self.save_format_form).pack(side="left", padx=5)
        help_text = ("Use this when Flipkart gives new files like ring/chain/car hanger. "
                     "Create/select format, write field lines as Label = column_header. Example: Color = color. "
                     "Detection works by file name keywords first, then matching Excel/CSV column headers. "
                     "If auto-detect is wrong, choose the file in Generate Labels, select Change selected format, then Apply.")
        ttk.Label(self.flipkart_map_frame, text=help_text, justify="left").pack(anchor="w", padx=14, pady=6)
        form = ttk.Frame(self.flipkart_map_frame)
        form.pack(fill="both", expand=True, padx=8, pady=8)
        self.format_entry = {}
        for i, (key, label) in enumerate([("key", "Format Key"), ("title", "Label Title"), ("generic", "Generic Name")]):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=5)
            ent = ttk.Entry(form, width=70)
            ent.grid(row=i, column=1, sticky="ew", padx=5, pady=5)
            self.format_entry[key] = ent
        ttk.Label(form, text="Fields / Column Mapping").grid(row=3, column=0, sticky="nw", padx=5, pady=5)
        self.fields_text = tk.Text(form, height=14, width=95)
        self.fields_text.grid(row=3, column=1, sticky="nsew", padx=5, pady=5)
        form.columnconfigure(1, weight=1)
        form.rowconfigure(3, weight=1)
        self.refresh_format_combos()
        self.build_amazon_settings_tab()

    def build_amazon_settings_tab(self):
        parent = self.amazon_map_frame
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="Default Amazon Branch:").pack(side="left")
        self.amazon_settings_branch_var = tk.StringVar(value=self.amazon_mapping.get("selected_branch", ""))
        self.amazon_settings_branch_combo = ttk.Combobox(top, textvariable=self.amazon_settings_branch_var, state="readonly", width=30)
        self.amazon_settings_branch_combo.pack(side="left", padx=6)
        ttk.Button(top, text="Save Amazon Settings", command=self.save_amazon_settings).pack(side="left", padx=6)

        rules_frame = ttk.Frame(parent)
        rules_frame.pack(fill="x", padx=8, pady=4)

        category_box = ttk.LabelFrame(rules_frame, text="Category Keyword Rules")
        category_box.pack(side="left", fill="both", expand=True, padx=(0, 6))
        category_top = ttk.Frame(category_box)
        category_top.pack(fill="x", padx=6, pady=6)
        ttk.Label(category_top, text="Main Heading:").pack(side="left")
        self.amazon_category_var = tk.StringVar()
        self.amazon_category_combo = ttk.Combobox(category_top, textvariable=self.amazon_category_var, state="readonly", width=28)
        self.amazon_category_combo.pack(side="left", padx=5)
        self.amazon_category_combo.bind("<<ComboboxSelected>>", lambda e: self.load_amazon_category_keywords())
        ttk.Label(category_top, text="Add:").pack(side="left", padx=(10, 3))
        self.amazon_new_category_var = tk.StringVar()
        ttk.Entry(category_top, textvariable=self.amazon_new_category_var, width=20).pack(side="left")
        ttk.Button(category_top, text="Add Category", command=self.add_amazon_category).pack(side="left", padx=5)
        self.amazon_keywords_text = tk.Text(category_box, height=7, width=58)
        self.amazon_keywords_text.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        ttk.Button(category_box, text="Save Category Keywords", command=self.save_amazon_category_keywords).pack(anchor="e", padx=6, pady=(0, 6))

        brand_box = ttk.LabelFrame(rules_frame, text="Brand List")
        brand_box.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self.amazon_brand_text = tk.Text(brand_box, height=9, width=38)
        self.amazon_brand_text.pack(fill="both", expand=True, padx=6, pady=6)
        ttk.Button(brand_box, text="Save Brand List", command=self.save_amazon_brand_list).pack(anchor="e", padx=6, pady=(0, 6))

        mapping_box = ttk.LabelFrame(parent, text="Column Mapping")
        mapping_box.pack(fill="both", expand=True, padx=8, pady=8)
        self.amazon_mapping_vars = {"consignment": {}, "master": {}}
        self.amazon_mapping_combos = {"consignment": {}, "master": {}}
        consignment_fields = [
            ("merchant_sku", "Merchant SKU"),
            ("title", "Title"),
            ("asin", "ASIN"),
            ("fnsku", "FNSKU"),
            ("shipped_qty", "Shipped Qty"),
            ("condition", "Condition"),
        ]
        master_fields = [
            ("item_name", "Item Name"),
            ("item_description", "Item Description"),
            ("seller_sku", "Seller SKU"),
            ("asin", "ASIN"),
            ("product_id", "Product ID"),
            ("mrp", "MRP"),
        ]
        left = ttk.Frame(mapping_box)
        right = ttk.Frame(mapping_box)
        left.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        ttk.Label(left, text="Amazon Consignment File").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Label(right, text="Weekly Master Listing").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        for i, (field, label) in enumerate(consignment_fields, start=1):
            ttk.Label(left, text=label).grid(row=i, column=0, sticky="w", padx=4, pady=3)
            var = tk.StringVar(value=self.amazon_mapping.get("consignment", {}).get(field, ""))
            combo = ttk.Combobox(left, textvariable=var, values=self.amazon_column_values("consignment"), width=38)
            combo.grid(row=i, column=1, sticky="ew", padx=4, pady=3)
            self.amazon_mapping_vars["consignment"][field] = var
            self.amazon_mapping_combos["consignment"][field] = combo
        for i, (field, label) in enumerate(master_fields, start=1):
            ttk.Label(right, text=label).grid(row=i, column=0, sticky="w", padx=4, pady=3)
            var = tk.StringVar(value=self.amazon_mapping.get("master", {}).get(field, ""))
            combo = ttk.Combobox(right, textvariable=var, values=self.amazon_column_values("master"), width=38)
            combo.grid(row=i, column=1, sticky="ew", padx=4, pady=3)
            self.amazon_mapping_vars["master"][field] = var
            self.amazon_mapping_combos["master"][field] = combo
        left.columnconfigure(1, weight=1)
        right.columnconfigure(1, weight=1)

        self.refresh_amazon_rule_widgets()

    def amazon_column_values(self, group):
        defaults = list(amazon_rules.DEFAULT_MAPPING_SETTINGS.get(group, {}).values())
        detected = []
        if group == "consignment" and self.amazon_consignment:
            detected = self.amazon_consignment.get("detected_columns", {}).get("consignment", [])
        elif group == "master" and self.amazon_master:
            detected = self.amazon_master.get("detected_columns", {}).get("master", [])
        elif self.amazon_workbook:
            detected = self.amazon_workbook.get("detected_columns", {}).get(group, [])
        return amazon_rules.unique_list(defaults + detected)

    def refresh_amazon_mapping_column_values(self):
        if not hasattr(self, "amazon_mapping_combos"):
            return
        for group, combos in self.amazon_mapping_combos.items():
            vals = self.amazon_column_values(group)
            for combo in combos.values():
                combo["values"] = vals

    def refresh_amazon_rule_widgets(self):
        if not hasattr(self, "amazon_category_combo"):
            return
        self.amazon_category_rules = amazon_rules.load_category_rules()
        self.amazon_brand_rules = amazon_rules.load_brand_rules()
        categories = self.amazon_category_rules.get("categories", amazon_rules.DEFAULT_CATEGORIES)
        self.amazon_category_combo["values"] = categories
        if not self.amazon_category_var.get() and categories:
            self.amazon_category_var.set(categories[0])
        self.load_amazon_category_keywords()
        self.amazon_brand_text.delete("1.0", "end")
        self.amazon_brand_text.insert("1.0", "\n".join(self.amazon_brand_rules.get("brands", amazon_rules.DEFAULT_BRANDS)))
        self.refresh_amazon_mapping_column_values()

    def load_amazon_category_keywords(self):
        if not hasattr(self, "amazon_keywords_text"):
            return
        category = self.amazon_category_var.get()
        keywords = self.amazon_category_rules.get("keyword_rules", {}).get(category, [])
        self.amazon_keywords_text.delete("1.0", "end")
        self.amazon_keywords_text.insert("1.0", "\n".join(keywords))

    def save_amazon_category_keywords(self):
        category = self.amazon_category_var.get().strip()
        if not category:
            messagebox.showwarning("No category", "Choose a Main Heading first.")
            return
        keywords = amazon_rules.split_keywords(self.amazon_keywords_text.get("1.0", "end"))
        self.amazon_category_rules.setdefault("keyword_rules", {})[category] = keywords
        if category not in self.amazon_category_rules.setdefault("categories", []):
            self.amazon_category_rules["categories"].append(category)
        amazon_rules.save_category_rules(self.amazon_category_rules)
        self.rebuild_amazon_rows()
        self.status_var.set("Amazon category keyword rules saved.")

    def add_amazon_category(self):
        category = self.amazon_new_category_var.get().strip()
        if not category:
            return
        self.amazon_category_rules = amazon_rules.load_category_rules()
        if category not in self.amazon_category_rules.setdefault("categories", []):
            self.amazon_category_rules["categories"].append(category)
            self.amazon_category_rules.setdefault("keyword_rules", {}).setdefault(category, [])
            amazon_rules.save_category_rules(self.amazon_category_rules)
        self.amazon_new_category_var.set("")
        self.amazon_category_var.set(category)
        self.refresh_amazon_rule_widgets()
        self.status_var.set(f"Amazon category added: {category}")

    def save_amazon_brand_list(self):
        brands = [line.strip() for line in self.amazon_brand_text.get("1.0", "end").splitlines() if line.strip()]
        self.amazon_brand_rules["brands"] = amazon_rules.unique_list(brands)
        amazon_rules.save_brand_rules(self.amazon_brand_rules)
        self.rebuild_amazon_rows()
        self.status_var.set("Amazon brand list saved.")

    def save_amazon_settings(self):
        if hasattr(self, "amazon_mapping_vars"):
            for group, fields in self.amazon_mapping_vars.items():
                self.amazon_mapping.setdefault(group, {})
                for field, var in fields.items():
                    self.amazon_mapping[group][field] = var.get().strip()
        if hasattr(self, "amazon_settings_branch_var"):
            self.amazon_mapping["selected_branch"] = self.amazon_settings_branch_var.get().strip()
            if self.amazon_mapping["selected_branch"]:
                self.amazon_branch_var.set(self.amazon_mapping["selected_branch"])
        amazon_rules.save_mapping_settings(self.amazon_mapping)
        self.rebuild_amazon_rows()
        self.status_var.set("Amazon mapping settings saved.")

    def save_amazon_selected_branch(self):
        if not hasattr(self, "amazon_branch_var"):
            return
        self.amazon_mapping["selected_branch"] = self.amazon_branch_var.get().strip()
        amazon_rules.save_mapping_settings(self.amazon_mapping)
        if hasattr(self, "amazon_settings_branch_var"):
            self.amazon_settings_branch_var.set(self.amazon_branch_var.get())
        self.rebuild_amazon_rows()

    def refresh_format_combos(self):
        vals = list(FORMATS.keys())
        try:
            self.change_format_combo["values"] = vals
            if vals and not self.change_format_var.get(): self.change_format_var.set(vals[0])
        except Exception:
            pass
        try:
            self.map_format_combo["values"] = vals
            if vals and not self.map_format_var.get(): self.map_format_var.set(vals[0])
            self.load_format_form()
        except Exception:
            pass

    def load_format_form(self):
        key = self.map_format_var.get() or (next(iter(FORMATS)) if FORMATS else "")
        cfg = FORMATS.get(key, {})
        for k, ent in self.format_entry.items():
            ent.delete(0, "end")
        self.format_entry["key"].insert(0, key)
        self.format_entry["title"].insert(0, cfg.get("title", ""))
        self.format_entry["generic"].insert(0, cfg.get("generic", ""))
        self.fields_text.delete("1.0", "end")
        for label, aliases in cfg.get("fields", []):
            first = aliases[0] if aliases else ""
            self.fields_text.insert("end", f"{label} = {first}\n")

    def save_format_form(self):
        old_key = self.map_format_var.get()
        key = norm_col(self.format_entry["key"].get() or old_key or "new_format")
        title = self.format_entry["title"].get().strip() or key.replace("_", " ").title()
        generic = self.format_entry["generic"].get().strip() or title
        fields = []
        for raw in self.fields_text.get("1.0", "end").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            if "=" in raw:
                label, col = raw.split("=", 1)
            else:
                label, col = raw, raw
            label = label.strip()
            aliases = [a.strip() for a in col.split(",") if a.strip()] or [label]
            fields.append((label, aliases))
        if old_key and old_key != key and old_key in FORMATS:
            del FORMATS[old_key]
        FORMATS[key] = {"title": title, "generic": generic, "fields": fields}
        save_formats(FORMATS)
        self.refresh_format_combos()
        self.map_format_var.set(key)
        self.change_format_var.set(key)
        self.status_var.set("Format mapping saved.")

    def add_format(self):
        key = f"new_format_{len(FORMATS)+1}"
        FORMATS[key] = {"title": "New Format", "generic": "New Format", "fields": [("Color", ["color"]), ("Model Number", ["model_number"]), ("Brand", ["brand"])]}
        save_formats(FORMATS)
        self.refresh_format_combos()
        self.map_format_var.set(key)
        self.load_format_form()

    def apply_selected_format(self):
        idx = self.selected_index()
        if idx is None:
            messagebox.showwarning("No selection", "Select a file first.")
            return
        fmt = self.change_format_var.get()
        if fmt not in FORMATS:
            return
        self.files[idx]["format"] = fmt
        item_id = self.file_tree.selection()[0]
        vals = list(self.file_tree.item(item_id, "values"))
        vals[1] = fmt
        self.file_tree.item(item_id, values=vals)
        self.status_var.set(f"Format changed to {fmt}. Click Preview Selected.")

    def refresh_branches(self):
        names = list(self.branches.keys()) or ["Mumbai Branch"]
        self.branch_combo["values"] = names
        self.settings_branch_combo["values"] = names
        if hasattr(self, "amazon_branch_combo"):
            self.amazon_branch_combo["values"] = names
        if hasattr(self, "amazon_settings_branch_combo"):
            self.amazon_settings_branch_combo["values"] = names
        if self.branch_var.get() not in names:
            self.branch_var.set(names[0])
        if self.settings_branch_var.get() not in names:
            self.settings_branch_var.set(names[0])
        preferred_amazon = self.amazon_mapping.get("selected_branch", "")
        if hasattr(self, "amazon_branch_var") and self.amazon_branch_var.get() not in names:
            self.amazon_branch_var.set(preferred_amazon if preferred_amazon in names else names[0])
        if hasattr(self, "amazon_settings_branch_var") and self.amazon_settings_branch_var.get() not in names:
            self.amazon_settings_branch_var.set(self.amazon_branch_var.get() if hasattr(self, "amazon_branch_var") else names[0])
        self.load_branch_form()

    def current_branch(self):
        return self.branches.get(self.branch_var.get()) or next(iter(self.branches.values()))

    def current_amazon_branch(self):
        if hasattr(self, "amazon_branch_var"):
            return self.branches.get(self.amazon_branch_var.get()) or self.current_branch()
        return self.current_branch()

    def load_branch_form(self):
        b = self.branches.get(self.settings_branch_var.get(), {})
        for k, ent in self.entry.items():
            ent.delete(0, "end")
            ent.insert(0, b.get(k, ""))

    def save_branch_form(self):
        data = {k: ent.get().strip() for k, ent in self.entry.items()}
        name = data.get("name") or self.settings_branch_var.get() or "New Branch"
        data["name"] = name
        old = self.settings_branch_var.get()
        if old and old != name and old in self.branches:
            del self.branches[old]
        self.branches[name] = data
        save_branches(self.branches)
        self.refresh_branches()
        self.branch_var.set(name)
        self.settings_branch_var.set(name)
        self.status_var.set("Branch settings saved.")

    def add_branch(self):
        name = f"Branch {len(self.branches)+1}"
        data = json.loads(json.dumps(DEFAULT_BRANCHES["Mumbai Branch"]))
        data["name"] = name
        self.branches[name] = data
        save_branches(self.branches)
        self.refresh_branches()
        self.settings_branch_var.set(name)
        self.load_branch_form()

    def delete_branch(self):
        name = self.settings_branch_var.get()
        if len(self.branches) <= 1:
            messagebox.showwarning("Cannot delete", "At least one branch is required.")
            return
        if messagebox.askyesno("Delete Branch", f"Delete {name}?"):
            self.branches.pop(name, None)
            save_branches(self.branches)
            self.refresh_branches()

    def upload_files(self):
        paths = filedialog.askopenfilenames(title="Select Flipkart CSV/XLSX files", filetypes=[("CSV/XLSX", "*.csv *.xlsx *.xls"), ("All Files", "*.*")])
        if paths:
            self.load_paths(paths)

    def load_samples(self):
        paths = list(SAMPLE_DIR.glob("Quality_Check*.csv"))
        self.load_paths([str(p) for p in paths])

    def load_paths(self, paths):
        self.status_var.set("Loading files. Please wait...")
        self.update_idletasks()
        loaded = 0
        errors = []
        for p in paths:
            try:
                if Path(p).suffix.lower() in (".xlsx", ".xls"):
                    try:
                        if amazon_reader.detect_amazon_workbook(p, self.amazon_mapping):
                            errors.append(f"{Path(p).name}: Amazon workbook detected. Use the Amazon Labels tab.")
                            continue
                        if amazon_reader.detect_master_listing_workbook(p, self.amazon_mapping):
                            errors.append(f"{Path(p).name}: Amazon master listing detected. Use the Amazon Labels tab.")
                            continue
                    except Exception:
                        pass
                df = read_file(p)
                fmt = detect_format(p, df)
                qty = {int(i): detect_qty(df, r) for i, r in df.iterrows()}
                self.files.append({"path": str(p), "df": df, "format": fmt, "qty": qty})
                self.file_tree.insert("", "end", values=(Path(p).name, fmt, len(df)))
                loaded += 1
            except Exception as e:
                errors.append(f"{Path(p).name}: {e}")
                log(traceback.format_exc())
        if self.file_tree.get_children() and not self.file_tree.selection():
            self.file_tree.selection_set(self.file_tree.get_children()[0])
            self.on_file_select_light(None)
        self.status_var.set(f"Loaded {loaded} file(s). Select a file and click Preview Selected.")
        if errors:
            messagebox.showerror("Load error", "\n".join(errors[:20]))

    def clear_files(self):
        self.files.clear()
        for tree in (self.file_tree, self.data_tree):
            for item in tree.get_children():
                tree.delete(item)
        self.show_empty_preview()
        self.status_var.set("Cleared files.")

    def selected_index(self):
        sel = self.file_tree.selection()
        if not sel:
            return None
        idx = self.file_tree.index(sel[0])
        if idx < 0 or idx >= len(self.files):
            return None
        return idx

    def on_file_select_light(self, event):
        idx = self.selected_index()
        if idx is None:
            return
        item = self.files[idx]
        df = item["df"]
        for row in self.data_tree.get_children():
            self.data_tree.delete(row)
        base_cols = list(df.columns)[:7]
        cols = ["Print Qty"] + base_cols
        self.data_tree["columns"] = cols
        self.data_tree["show"] = "headings"
        for c in cols:
            self.data_tree.heading(c, text=str(c)[:20])
            self.data_tree.column(c, width=90 if c == "Print Qty" else 125, anchor="w")
        for ridx, r in df.head(50).iterrows():
            values = [get_row_qty(item, ridx)] + [clean_val(r.get(c, ""))[:45] for c in base_cols]
            self.data_tree.insert("", "end", iid=str(int(ridx)), values=values)
        self.preview.delete("all")
        self.preview.create_text(30, 30, text="Click 'Preview Selected' to render label preview", anchor="nw", fill="#555555", font=("Arial", 16, "bold"))
        self.status_var.set(f"Selected {Path(item['path']).name}. Click Preview Selected.")

    def on_data_row_select(self, event=None):
        idx = self.selected_index()
        sel = self.data_tree.selection()
        if idx is None or not sel:
            return
        try:
            ridx = int(sel[0])
            self.row_qty_var.set(str(get_row_qty(self.files[idx], ridx)))
        except Exception:
            pass

    def apply_row_qty(self):
        idx = self.selected_index()
        sel = self.data_tree.selection()
        if idx is None or not sel:
            messagebox.showwarning("No row", "Select a row in data preview first.")
            return
        qty = safe_int(self.row_qty_var.get(), 1)
        ridx = int(sel[0])
        self.files[idx].setdefault("qty", {})[ridx] = qty
        vals = list(self.data_tree.item(sel[0], "values"))
        if vals:
            vals[0] = qty
            self.data_tree.item(sel[0], values=vals)
        self.status_var.set(f"Print quantity updated to {qty} for selected row.")

    def quick_set_selected_qty(self):
        idx = self.selected_index()
        sel = self.data_tree.selection()
        if idx is None or not sel:
            messagebox.showwarning("No SKU selected", "Select one SKU row first, then set quantity.")
            return
        current = self.row_qty_var.get() or "1"
        qty = simpledialog.askinteger("Set Print Quantity", "How many labels do you need for this selected SKU?\nExample: type 100 for 100 repeated labels.", initialvalue=safe_int(current, 1), minvalue=1, maxvalue=100000, parent=self)
        if qty is None:
            return
        self.row_qty_var.set(str(qty))
        self.apply_row_qty()

    def on_data_tree_double_click(self, event=None):
        # Double-click any selected SKU row to quickly enter print quantity.
        self.quick_set_selected_qty()

    def apply_qty_to_all_rows(self):
        idx = self.selected_index()
        if idx is None:
            messagebox.showwarning("No file", "Select a file first.")
            return
        qty = safe_int(self.row_qty_var.get(), 1)
        item = self.files[idx]
        item["qty"] = {int(i): qty for i in range(len(item["df"]))}
        self.on_file_select_light(None)
        self.status_var.set(f"All rows in selected file set to quantity {qty}.")

    def edit_quantities_dialog(self):
        idx = self.selected_index()
        if idx is None:
            messagebox.showwarning("No file", "Select a file first.")
            return
        item = self.files[idx]
        df = item["df"]
        win = tk.Toplevel(self)
        win.title("Edit Print Quantities")
        win.geometry("900x520")
        win.transient(self)
        top = ttk.Frame(win)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="Type quantity for each SKU. PDF will repeat each label by this quantity.").pack(side="left")
        cols = ("row", "qty", "sku", "fsn", "model")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=18)
        headings = {"row":"Row", "qty":"Print Qty", "sku":"SKU", "fsn":"FSN", "model":"Model Number"}
        widths = {"row":60, "qty":90, "sku":130, "fsn":160, "model":430}
        for ccol in cols:
            tree.heading(ccol, text=headings[ccol])
            tree.column(ccol, width=widths[ccol], anchor="w")
        tree.pack(fill="both", expand=True, padx=8, pady=4)
        for ridx, r in df.iterrows():
            sku = row_value(df, r, ["SKU", "sku"], "")
            fsn = row_value(df, r, ["FSN", "fsn"], "")
            model = row_value(df, r, ["model_number", "model no", "model"], "")
            tree.insert("", "end", iid=str(int(ridx)), values=(int(ridx)+1, get_row_qty(item, ridx), sku, fsn, model[:80]))
        edit_box = None
        def edit_cell(event=None):
            nonlocal edit_box
            sel = tree.selection()
            if not sel:
                return
            rowid = sel[0]
            bbox = tree.bbox(rowid, "qty")
            if not bbox:
                return
            x, y, w, h = bbox
            if edit_box:
                edit_box.destroy()
            edit_box = ttk.Entry(tree, width=8)
            edit_box.place(x=x, y=y, width=w, height=h)
            current = str(tree.set(rowid, "qty"))
            edit_box.insert(0, current)
            edit_box.focus_set()
            edit_box.select_range(0, "end")
            def save_edit(e=None):
                q = safe_int(edit_box.get(), 1)
                tree.set(rowid, "qty", q)
                edit_box.destroy()
            edit_box.bind("<Return>", save_edit)
            edit_box.bind("<FocusOut>", save_edit)
        tree.bind("<Double-1>", edit_cell)
        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=8, pady=8)
        ttk.Label(btns, text="Double-click the Print Qty cell to edit.").pack(side="left")
        def save_all():
            qty_map = {}
            for iid in tree.get_children():
                qty_map[int(iid)] = safe_int(tree.set(iid, "qty"), 1)
            item["qty"] = qty_map
            self.on_file_select_light(None)
            self.status_var.set("Print quantities saved.")
            win.destroy()
        ttk.Button(btns, text="Save Quantities", command=save_all).pack(side="right", padx=4)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right", padx=4)

    def set_all_qty_one(self):
        idx = self.selected_index()
        if idx is None:
            return
        item = self.files[idx]
        item["qty"] = {int(i): 1 for i in range(len(item["df"]))}
        self.on_file_select_light(None)
        self.status_var.set("All print quantities set to 1 for selected file.")

    def sync_amazon_mapping_from_widgets(self):
        if not hasattr(self, "amazon_mapping_vars"):
            return
        for group, fields in self.amazon_mapping_vars.items():
            self.amazon_mapping.setdefault(group, {})
            for field, var in fields.items():
                self.amazon_mapping[group][field] = var.get().strip()

    def update_amazon_file_status(self):
        if hasattr(self, "amazon_master_status_var"):
            if self.amazon_master:
                name = Path(self.amazon_master_path or self.amazon_master.get("path", "")).name
                row_count = len(self.amazon_master_df) if self.amazon_master_df is not None else 0
                mrp_col = self.amazon_master.get("mrp_col", "") or "not detected"
                self.amazon_master_status_var.set(f"Master Listing: {name} | rows: {row_count} | MRP column: {mrp_col}")
            else:
                self.amazon_master_status_var.set("Master Listing: not loaded")
        if hasattr(self, "amazon_consignment_status_var"):
            if self.amazon_consignment:
                name = Path(self.amazon_consignment_path or self.amazon_consignment.get("path", "")).name
                row_count = len(self.amazon_consignment_df) if self.amazon_consignment_df is not None else 0
                sheet = self.amazon_consignment.get("consignment_sheet", "") or "not detected"
                header = self.amazon_consignment.get("consignment_header_row")
                header_text = f"row {int(header) + 1}" if header is not None else "not detected"
                self.amazon_consignment_status_var.set(f"Consignment File: {name} | rows: {row_count} | label sheet: {sheet}/{header_text}")
            else:
                self.amazon_consignment_status_var.set("Consignment File: not loaded")

    def try_auto_load_amazon_master(self):
        path = self.amazon_mapping.get("last_master_path", "")
        candidates = []
        if path:
            candidates.append(Path(path))
        candidates.append(CURRENT_AMAZON_MASTER_FILE)
        for candidate in candidates:
            if candidate.exists():
                try:
                    if self.load_amazon_master_path(str(candidate), copy_to_current=False, quiet=True):
                        self.status_var.set(f"Auto-loaded Amazon master listing: {candidate.name}")
                        return
                except Exception:
                    log(traceback.format_exc())
        self.update_amazon_file_status()

    def upload_amazon_master_file(self):
        path = filedialog.askopenfilename(title="Select weekly Amazon master listing", filetypes=[("Excel Workbook", "*.xlsx *.xls"), ("All Files", "*.*")])
        if path:
            self.load_amazon_master_path(path)

    def load_amazon_master_path(self, path, copy_to_current=True, quiet=False):
        self.sync_amazon_mapping_from_widgets()
        self.status_var.set("Loading Amazon weekly master listing...")
        self.update_idletasks()
        try:
            master = amazon_reader.load_master_listing_file(path, self.amazon_mapping)
            self.amazon_master = master
            self.amazon_master_df = master.get("master_df")
            self.amazon_master_path = str(path)
            self.amazon_mapping["last_master_path"] = str(path)
            amazon_rules.save_mapping_settings(self.amazon_mapping)
            if copy_to_current:
                try:
                    shutil.copy2(path, CURRENT_AMAZON_MASTER_FILE)
                except Exception:
                    log(traceback.format_exc())
            self.amazon_manual_mrp = {}
            self.refresh_amazon_mapping_column_values()
            self.rebuild_amazon_rows(preserve_quantities=True)
            self.update_amazon_file_status()
            if not quiet:
                row_count = len(self.amazon_master_df) if self.amazon_master_df is not None else 0
                self.status_var.set(f"Amazon master listing loaded: {row_count} row(s).")
            return True
        except Exception as e:
            log(traceback.format_exc())
            if not quiet:
                messagebox.showerror("Amazon master load error", str(e))
                self.status_var.set("Amazon master listing load failed.")
            else:
                self.update_amazon_file_status()
            return False

    def upload_amazon_consignment_file(self):
        path = filedialog.askopenfilename(title="Select Amazon consignment label file", filetypes=[("Excel Workbook", "*.xlsx *.xls"), ("All Files", "*.*")])
        if path:
            self.load_amazon_consignment_path(path)

    def load_amazon_consignment_path(self, path):
        self.sync_amazon_mapping_from_widgets()
        self.status_var.set("Loading Amazon consignment file...")
        self.update_idletasks()
        try:
            consignment = amazon_reader.load_consignment_file(path, self.amazon_mapping)
            amazon_rules.merge_sheet_options(consignment.get("sheet_categories", []), consignment.get("sheet_brands", []))
            self.amazon_consignment = consignment
            self.amazon_consignment_df = consignment.get("consignment_df")
            self.amazon_consignment_path = str(path)
            self.amazon_manual_mrp = {}
            self.amazon_qty_overrides = {}

            # Backward-compatible convenience: if the consignment workbook also has a master sheet and no master is loaded, use it.
            if self.amazon_master is None:
                try:
                    master = amazon_reader.load_master_listing_file(path, self.amazon_mapping)
                    self.amazon_master = master
                    self.amazon_master_df = master.get("master_df")
                    self.amazon_master_path = str(path)
                except Exception:
                    pass

            self.refresh_amazon_rule_widgets()
            self.refresh_amazon_mapping_column_values()
            self.rebuild_amazon_rows(preserve_quantities=False)
            self.update_amazon_file_status()
            row_count = len(self.amazon_consignment_df) if self.amazon_consignment_df is not None else 0
            if self.amazon_master is None:
                self.status_var.set(f"Amazon consignment loaded: {row_count} row(s). Upload Weekly Master Listing to auto-fill MRP.")
            else:
                self.status_var.set(f"Amazon consignment loaded: {row_count} row(s).")
        except Exception as e:
            log(traceback.format_exc())
            messagebox.showerror("Amazon consignment load error", str(e))
            self.status_var.set("Amazon consignment load failed.")

    def load_amazon_path(self, path):
        # Backward-compatible combined-workbook loader.
        self.sync_amazon_mapping_from_widgets()
        self.status_var.set("Loading Amazon workbook. Please wait...")
        self.update_idletasks()
        try:
            workbook = amazon_reader.load_amazon_workbook(path, self.amazon_mapping)
            amazon_rules.merge_sheet_options(workbook.get("sheet_categories", []), workbook.get("sheet_brands", []))
            self.amazon_workbook = workbook
            self.amazon_consignment = {
                "path": str(path),
                "sheet_names": workbook.get("sheet_names", []),
                "consignment_sheet": workbook.get("consignment_sheet", ""),
                "consignment_header_row": workbook.get("consignment_header_row"),
                "consignment_df": workbook.get("consignment_df"),
                "need_sheet": workbook.get("need_sheet", ""),
                "sheet_categories": workbook.get("sheet_categories", []),
                "sheet_brands": workbook.get("sheet_brands", []),
                "detected_columns": {"consignment": workbook.get("detected_columns", {}).get("consignment", [])},
            }
            self.amazon_consignment_df = workbook.get("consignment_df")
            self.amazon_consignment_path = str(path)
            if workbook.get("master_df") is not None and not workbook.get("master_df").empty:
                self.amazon_master = {
                    "path": str(path),
                    "master_sheet": workbook.get("master_sheet", ""),
                    "master_header_row": workbook.get("master_header_row"),
                    "master_df": workbook.get("master_df"),
                    "mrp_col": workbook.get("mrp_col", ""),
                    "detected_columns": {"master": workbook.get("detected_columns", {}).get("master", [])},
                }
                self.amazon_master_df = workbook.get("master_df")
                self.amazon_master_path = str(path)
            self.amazon_manual_mrp = {}
            self.amazon_qty_overrides = {}
            self.refresh_amazon_rule_widgets()
            self.refresh_amazon_mapping_column_values()
            self.rebuild_amazon_rows(preserve_quantities=False)
            self.update_amazon_file_status()
            self.status_var.set(f"Amazon workbook loaded: {len(self.amazon_rows)} row(s).")
        except Exception as e:
            log(traceback.format_exc())
            messagebox.showerror("Amazon load error", str(e))
            self.status_var.set("Amazon workbook load failed.")

    def upload_amazon_workbook(self):
        path = filedialog.askopenfilename(title="Select combined Amazon workbook", filetypes=[("Excel Workbook", "*.xlsx *.xls"), ("All Files", "*.*")])
        if path:
            self.load_amazon_path(path)

    def clear_amazon(self):
        self.clear_amazon_consignment()
        self.clear_amazon_master()
        self.status_var.set("Cleared Amazon files.")

    def clear_amazon_consignment(self):
        self.amazon_workbook = None
        self.amazon_consignment = None
        self.amazon_consignment_df = None
        self.amazon_consignment_path = ""
        self.amazon_rows = []
        self.amazon_manual_mrp = {}
        self.amazon_qty_overrides = {}
        for item in self.amazon_tree.get_children():
            self.amazon_tree.delete(item)
        self.amazon_preview.delete("all")
        self.amazon_preview.create_text(30, 30, text="Upload Amazon consignment file to preview", anchor="nw", fill="#777777", font=("Arial", 16, "bold"))
        self.update_amazon_file_status()
        self.status_var.set("Cleared Amazon consignment file.")

    def clear_amazon_master(self):
        self.amazon_master = None
        self.amazon_master_df = None
        self.amazon_master_path = ""
        self.amazon_manual_mrp = {}
        self.amazon_mapping["last_master_path"] = ""
        amazon_rules.save_mapping_settings(self.amazon_mapping)
        try:
            if CURRENT_AMAZON_MASTER_FILE.exists():
                CURRENT_AMAZON_MASTER_FILE.unlink()
        except Exception:
            log(traceback.format_exc())
        self.rebuild_amazon_rows(preserve_quantities=True)
        self.update_amazon_file_status()
        self.status_var.set("Cleared Amazon master listing.")

    def rebuild_amazon_rows(self, preserve_quantities=True):
        if self.amazon_consignment_df is None:
            return
        if preserve_quantities:
            for row in self.amazon_rows:
                if row.get("row_key"):
                    self.amazon_qty_overrides[row["row_key"]] = row.get("print_qty", "")
        self.sync_amazon_mapping_from_widgets()
        self.amazon_category_rules = amazon_rules.load_category_rules()
        self.amazon_brand_rules = amazon_rules.load_brand_rules()
        self.amazon_rows = amazon_validation.resolve_amazon_rows(
            self.amazon_consignment_df,
            self.amazon_mapping,
            self.amazon_category_rules,
            self.amazon_brand_rules,
            manual_mrp=self.amazon_manual_mrp,
            qty_overrides=self.amazon_qty_overrides,
            master_df=self.amazon_master_df,
        )
        amazon_validation.validate_amazon_rows(self.amazon_rows, self.current_amazon_branch())
        self.refresh_amazon_table()

    def refresh_amazon_table(self):
        if not hasattr(self, "amazon_tree"):
            return
        for item in self.amazon_tree.get_children():
            self.amazon_tree.delete(item)
        self.amazon_tree.tag_configure("PASS", background="#eaf7ea")
        self.amazon_tree.tag_configure("FAIL", background="#fdecec")
        for idx, row in enumerate(self.amazon_rows):
            values = (
                row.get("status", ""),
                row.get("merchant_sku", ""),
                row.get("asin", ""),
                row.get("fnsku", ""),
                row.get("title", "")[:80],
                row.get("main_heading", ""),
                row.get("brand", ""),
                row.get("mrp", ""),
                row.get("print_qty", ""),
                "; ".join(row.get("errors", [])),
            )
            self.amazon_tree.insert("", "end", iid=str(idx), values=values, tags=(row.get("status", ""),))
        if self.amazon_rows and not self.amazon_tree.selection():
            self.amazon_tree.selection_set("0")
            self.on_amazon_row_select()

    def validate_amazon_clicked(self):
        if self.amazon_consignment_df is None:
            messagebox.showwarning("No Amazon consignment", "Upload an Amazon consignment file first.")
            return
        self.rebuild_amazon_rows()
        fail_count = sum(1 for row in self.amazon_rows if row.get("errors"))
        if fail_count:
            extra = "\n\nUpload Weekly Master Listing to auto-fill MRP." if self.amazon_master_df is None else ""
            messagebox.showwarning("Amazon validation issues", f"{fail_count} row(s) have blocking issues. Use Fix Blocking Rows before generating PDF.{extra}")
            self.status_var.set(f"Amazon validation found {fail_count} failing row(s).")
        else:
            messagebox.showinfo("Amazon validation PASS", "All Amazon rows passed validation.")
            self.status_var.set("Amazon validation PASS.")

    def selected_amazon_row_index(self):
        sel = self.amazon_tree.selection()
        if not sel:
            return None
        try:
            idx = int(sel[0])
            if 0 <= idx < len(self.amazon_rows):
                return idx
        except Exception:
            pass
        return None

    def on_amazon_row_select(self, event=None):
        idx = self.selected_amazon_row_index()
        if idx is None:
            return
        self.amazon_qty_var.set(str(self.amazon_rows[idx].get("print_qty", "1")))
        if hasattr(self, "amazon_preview"):
            self.amazon_preview.delete("all")
            self.amazon_preview.create_text(30, 30, text="Click Preview Selected", anchor="nw", fill="#777777", font=("Arial", 16, "bold"))

    def apply_amazon_row_qty(self):
        idx = self.selected_amazon_row_index()
        if idx is None:
            messagebox.showwarning("No Amazon row", "Select an Amazon row first.")
            return
        qty = amazon_validation.parse_positive_int(self.amazon_qty_var.get())
        if qty <= 0:
            messagebox.showwarning("Invalid quantity", "Print quantity must be greater than zero.")
            return
        row = self.amazon_rows[idx]
        self.amazon_qty_overrides[row["row_key"]] = qty
        row["print_qty"] = qty
        amazon_validation.validate_amazon_rows(self.amazon_rows, self.current_amazon_branch())
        self.refresh_amazon_table()
        self.amazon_tree.selection_set(str(idx))
        self.status_var.set(f"Amazon print quantity updated to {qty}.")

    def quick_set_amazon_qty(self, event=None):
        idx = self.selected_amazon_row_index()
        if idx is None:
            return
        current = self.amazon_qty_var.get() or "1"
        qty = simpledialog.askinteger("Set Amazon Print Quantity", "How many labels do you need for this selected SKU?", initialvalue=amazon_validation.parse_positive_int(current) or 1, minvalue=1, maxvalue=100000, parent=self)
        if qty is None:
            return
        self.amazon_qty_var.set(str(qty))
        self.apply_amazon_row_qty()

    def apply_amazon_qty_to_all_rows(self):
        if not self.amazon_rows:
            return
        qty = amazon_validation.parse_positive_int(self.amazon_qty_var.get())
        if qty <= 0:
            messagebox.showwarning("Invalid quantity", "Print quantity must be greater than zero.")
            return
        for row in self.amazon_rows:
            self.amazon_qty_overrides[row["row_key"]] = qty
            row["print_qty"] = qty
        amazon_validation.validate_amazon_rows(self.amazon_rows, self.current_amazon_branch())
        self.refresh_amazon_table()
        self.status_var.set(f"All Amazon rows set to quantity {qty}.")

    def reset_amazon_qty_from_shipped(self):
        self.amazon_qty_overrides = {}
        self.rebuild_amazon_rows(preserve_quantities=False)
        self.status_var.set("Amazon quantities reset from Shipped column.")

    def preview_selected_amazon(self):
        idx = self.selected_amazon_row_index()
        if idx is None:
            messagebox.showwarning("No Amazon row", "Select an Amazon row first.")
            return
        self.draw_amazon_canvas_label(self.amazon_rows[idx], self.current_amazon_branch())
        self.status_var.set("Amazon preview rendered.")

    def draw_amazon_canvas_label(self, row, branch):
        c = self.amazon_preview
        c.delete("all")
        W = max(c.winfo_width(), 560)
        H = max(c.winfo_height(), 560)
        size = min(W - 50, H - 62)
        size = max(330, size)
        x0 = max(18, (W - size) / 2)
        y0 = 18
        scale = size / 50.0
        c.create_rectangle(x0, y0, x0 + size, y0 + size, fill="white", outline="black", width=2)
        heading_font = min(24, max(14, int(2.25 * scale)))
        body_font = min(12, max(8, int(0.92 * scale)))
        small_font = min(11, max(7, int(0.78 * scale)))
        heading = amazon_label_renderer.amazon_display_heading(row.get("main_heading", ""))
        brand = row.get("brand", "")
        fnsku = row.get("fnsku", "")
        c.create_text(x0 + size / 2, y0 + 4.8 * scale, text=heading[:34], anchor="n", font=("Arial", heading_font, "bold"))
        y = y0 + 8.7 * scale
        fields = [
            ("Brand", brand),
            ("SKU No", row.get("merchant_sku", "")),
            ("Net Quantity", "1 N"),
            ("MRP", amazon_label_renderer.amazon_mrp_for_print(row.get("mrp", ""))),
            ("Generic Name", amazon_label_renderer.amazon_display_heading(row.get("generic_name", "")) or heading),
        ]
        for label, value in fields:
            c.create_text(x0 + 2.5 * scale, y, text=label, anchor="nw", font=("Arial", body_font))
            c.create_text(x0 + 16.0 * scale, y, text=":", anchor="nw", font=("Arial", body_font))
            c.create_text(x0 + 17.2 * scale, y, text=str(value)[:42], anchor="nw", font=("Arial", body_font))
            y += 1.75 * scale
        y += 0.6 * scale
        care = "Manufactured by / Marketed By / Customer care Details:"
        c.create_text(x0 + 2.5 * scale, y, text=care, anchor="nw", font=("Arial", small_font, "bold"))
        c.create_line(x0 + 2.5 * scale, y + 1.3 * scale, x0 + size - 2.2 * scale, y + 1.3 * scale, width=1)
        y += 2.1 * scale
        address_lines = []
        for line in amazon_label_renderer.branch_address_lines(branch):
            address_lines.extend(amazon_label_renderer.wrap_text(line, 42)[:2])
        address_lines.extend([
            f"Email Id:{branch.get('email', '')}",
            f"Contact:{branch.get('phone', '')}",
            f"Origin:{amazon_label_renderer.branch_origin_for_print(branch)}",
        ])
        for line in address_lines:
            if y > y0 + 35.2 * scale:
                break
            c.create_text(x0 + 2.7 * scale, y, text=line, anchor="nw", font=("Arial", small_font))
            y += 1.25 * scale
        bx0 = x0 + 4.4 * scale
        by0 = y0 + 36.3 * scale
        bw = 41.0 * scale
        bh = 6.6 * scale
        seed = sum(ord(ch) for ch in fnsku)
        for i in range(135):
            if (i + seed) % 4 != 0:
                xx = bx0 + i * bw / 135
                c.create_line(xx, by0, xx, by0 + bh, width=1)
        c.create_text(x0 + size / 2, y0 + 44.2 * scale, text=fnsku, anchor="n", font=("Arial", small_font))
        c.create_text(x0 + size / 2, y0 + 47.3 * scale, text=amazon_label_renderer.amazon_title_for_print(row.get("title", ""))[:58], anchor="n", font=("Arial", max(7, small_font - 1)))

    def amazon_blocking_items(self):
        items = []
        for idx, row in enumerate(self.amazon_rows):
            for error in row.get("errors", []):
                items.append((idx, error))
        return items

    def fix_amazon_blockers_dialog(self):
        if self.amazon_consignment_df is None:
            messagebox.showwarning("No Amazon consignment", "Upload an Amazon consignment file first.")
            return
        self.rebuild_amazon_rows()
        blockers = self.amazon_blocking_items()
        if not blockers:
            messagebox.showinfo("No blockers", "All Amazon rows are ready.")
            return

        win = tk.Toplevel(self)
        win.title("Fix Amazon Blocking Rows")
        win.geometry("1050x560")
        win.transient(self)
        win.grab_set()

        cols = ("sku", "asin", "fnsku", "title", "missing")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=14)
        widths = {"sku": 150, "asin": 120, "fnsku": 130, "title": 420, "missing": 190}
        headings = {"sku": "SKU", "asin": "ASIN", "fnsku": "FNSKU", "title": "Title", "missing": "Missing field"}
        for col in cols:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor="w")
        tree.pack(fill="both", expand=True, padx=8, pady=8)

        controls = ttk.Frame(win)
        controls.pack(fill="x", padx=8, pady=8)
        ttk.Label(controls, text="Main Heading:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(controls, textvariable=category_var, values=self.amazon_category_rules.get("categories", amazon_rules.DEFAULT_CATEGORIES), state="readonly", width=28)
        category_combo.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Button(controls, text="Save Rule / Apply", command=lambda: apply_category()).grid(row=0, column=2, sticky="w", padx=4, pady=4)

        ttk.Label(controls, text="Brand Name:").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        brand_var = tk.StringVar()
        brand_combo = ttk.Combobox(controls, textvariable=brand_var, values=self.amazon_brand_rules.get("brands", amazon_rules.DEFAULT_BRANDS), width=28)
        brand_combo.grid(row=1, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(controls, text="New brand:").grid(row=1, column=2, sticky="e", padx=4, pady=4)
        new_brand_var = tk.StringVar()
        ttk.Entry(controls, textvariable=new_brand_var, width=24).grid(row=1, column=3, sticky="w", padx=4, pady=4)
        ttk.Button(controls, text="Save Brand / Apply", command=lambda: apply_brand()).grid(row=1, column=4, sticky="w", padx=4, pady=4)

        ttk.Label(controls, text="MRP:").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        mrp_var = tk.StringVar()
        ttk.Entry(controls, textvariable=mrp_var, width=18).grid(row=2, column=1, sticky="w", padx=4, pady=4)
        ttk.Button(controls, text="Apply for this print", command=lambda: apply_mrp()).grid(row=2, column=2, sticky="w", padx=4, pady=4)
        info_var = tk.StringVar(value="For missing SKU/FNSKU/quantity, fix the workbook row or quantity grid. For branch errors, fill Branch / Address Settings.")
        ttk.Label(controls, textvariable=info_var).grid(row=3, column=0, columnspan=5, sticky="w", padx=4, pady=8)

        def refill_tree():
            for item in tree.get_children():
                tree.delete(item)
            for ridx, error in self.amazon_blocking_items():
                row = self.amazon_rows[ridx]
                iid = f"{ridx}|{error}"
                tree.insert("", "end", iid=iid, values=(row.get("merchant_sku", ""), row.get("asin", ""), row.get("fnsku", ""), row.get("title", "")[:90], error))
            if tree.get_children():
                tree.selection_set(tree.get_children()[0])
                on_select()

        def selected_dialog_row():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("No row", "Select a blocking row first.", parent=win)
                return None, ""
            raw = sel[0]
            idx_text, error = raw.split("|", 1)
            return int(idx_text), error

        def on_select(event=None):
            ridx, error = selected_dialog_row()
            if ridx is None:
                return
            row = self.amazon_rows[ridx]
            category_var.set(row.get("main_heading", "") or (self.amazon_category_rules.get("categories", amazon_rules.DEFAULT_CATEGORIES)[0]))
            brand_var.set(row.get("brand", "") or (self.amazon_brand_rules.get("brands", amazon_rules.DEFAULT_BRANDS)[0]))
            mrp_var.set(row.get("mrp", ""))
            info_var.set(f"Selected missing field: {error}")

        def after_apply():
            self.rebuild_amazon_rows()
            self.refresh_amazon_rule_widgets()
            category_combo["values"] = self.amazon_category_rules.get("categories", amazon_rules.DEFAULT_CATEGORIES)
            brand_combo["values"] = self.amazon_brand_rules.get("brands", amazon_rules.DEFAULT_BRANDS)
            refill_tree()
            if not tree.get_children():
                messagebox.showinfo("Amazon rows fixed", "All blocking Amazon rows are fixed.", parent=win)
                win.destroy()

        def apply_category():
            ridx, error = selected_dialog_row()
            if ridx is None:
                return
            if error != "Missing Main Heading":
                messagebox.showwarning("Wrong field", "Select a row missing Main Heading.", parent=win)
                return
            category = category_var.get().strip()
            if not category:
                return
            amazon_rules.save_category_manual_rule(self.amazon_rows[ridx], category)
            after_apply()

        def apply_brand():
            ridx, error = selected_dialog_row()
            if ridx is None:
                return
            if error != "Missing Brand Name":
                messagebox.showwarning("Wrong field", "Select a row missing Brand Name.", parent=win)
                return
            brand = new_brand_var.get().strip() or brand_var.get().strip()
            if not brand:
                return
            amazon_rules.save_brand_manual_rule(self.amazon_rows[ridx], brand)
            new_brand_var.set("")
            after_apply()

        def apply_mrp():
            ridx, error = selected_dialog_row()
            if ridx is None:
                return
            if error != "Missing MRP":
                messagebox.showwarning("Wrong field", "Select a row missing MRP.", parent=win)
                return
            mrp = amazon_validation.normalize_mrp(mrp_var.get())
            if not mrp:
                messagebox.showwarning("Invalid MRP", "Enter a valid MRP amount.", parent=win)
                return
            row = self.amazon_rows[ridx]
            self.amazon_manual_mrp[row["row_key"]] = mrp
            after_apply()

        tree.bind("<<TreeviewSelect>>", on_select)
        refill_tree()

    def total_amazon_print_labels(self):
        return sum(amazon_validation.parse_positive_int(row.get("print_qty", 0)) for row in self.amazon_rows)

    def prepare_amazon_generation(self, output_kind):
        if self.amazon_consignment_df is None:
            messagebox.showwarning("No Amazon consignment", "Upload an Amazon consignment file first.")
            return None
        self.rebuild_amazon_rows()
        if amazon_validation.has_blocking_errors(self.amazon_rows):
            self.fix_amazon_blockers_dialog()
            self.status_var.set(f"Amazon {output_kind} blocked until validation issues are fixed.")
            return None
        total = self.total_amazon_print_labels()
        if total <= 0:
            messagebox.showerror("No labels", "Amazon print quantity is zero.")
            return None
        if total > 20000:
            messagebox.showerror("Too many labels", f"You selected {total} labels. Please split into batches. Maximum 20,000 labels at once.")
            return None
        if total > 2000:
            ok = messagebox.askyesno(f"Large Amazon {output_kind}", f"You are generating {total} Amazon labels. This can take time and create a large file. Continue?")
            if not ok:
                return None
        return total

    def generate_amazon_pdf_clicked(self):
        if pdfcanvas is None or amazon_label_renderer.pdfcanvas is None:
            messagebox.showerror("Missing package", "reportlab missing. Run install_requirements.bat.")
            return
        total = self.prepare_amazon_generation("PDF")
        if total is None:
            return

        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = str(OUT_DIR / f"amazon_labels_{stamp}.pdf")
        report_out = str(OUT_DIR / f"amazon_label_report_{stamp}.csv")
        rows_snapshot = copy.deepcopy(self.amazon_rows)
        branch = copy.deepcopy(self.current_amazon_branch())
        try:
            self.amazon_generate_btn.config(state="disabled")
        except Exception:
            pass
        self.status_var.set(f"Generating {total} Amazon labels in background... app will stay usable.")
        self.update_idletasks()

        def progress(done, grand_total):
            self.after(0, lambda d=done, t=grand_total: self.status_var.set(f"Generating Amazon PDF... {d}/{t} labels done"))

        def worker():
            try:
                amazon_validation.write_report_csv(report_out, rows_snapshot)
                amazon_label_renderer.generate_amazon_pdf(out, rows_snapshot, branch, progress_callback=progress)
                self.after(0, lambda: self.on_amazon_pdf_done(out, report_out, total))
            except Exception as e:
                err = str(e)
                log(traceback.format_exc())
                self.after(0, lambda: self.on_amazon_pdf_error(err))

        threading.Thread(target=worker, daemon=True).start()

    def generate_amazon_prn_clicked(self):
        self.start_amazon_prn_generation(print_after=False)

    def generate_amazon_prn_and_print_clicked(self):
        self.start_amazon_prn_generation(print_after=True)

    def start_amazon_prn_generation(self, print_after=False):
        total = self.prepare_amazon_generation("PRN")
        if total is None:
            return

        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = str(OUT_DIR / f"amazon_labels_{stamp}.prn")
        report_out = str(OUT_DIR / f"amazon_label_report_{stamp}.csv")
        rows_snapshot = copy.deepcopy(self.amazon_rows)
        branch = copy.deepcopy(self.current_amazon_branch())
        try:
            self.amazon_prn_btn.config(state="disabled")
            if hasattr(self, "amazon_prn_print_btn"):
                self.amazon_prn_print_btn.config(state="disabled")
        except Exception:
            pass
        self.status_var.set(f"Generating {total} Amazon PRN labels in background... app will stay usable.")
        self.update_idletasks()

        def progress(done, grand_total):
            self.after(0, lambda d=done, t=grand_total: self.status_var.set(f"Generating Amazon PRN... {d}/{t} labels done"))

        def worker():
            try:
                amazon_validation.write_report_csv(report_out, rows_snapshot)
                amazon_prn_renderer.generate_amazon_prn(out, rows_snapshot, branch, progress_callback=progress)
                self.after(0, lambda: self.on_amazon_prn_done(out, report_out, total, print_after=print_after))
            except Exception as e:
                err = str(e)
                log(traceback.format_exc())
                self.after(0, lambda: self.on_amazon_prn_error(err))

        threading.Thread(target=worker, daemon=True).start()

    def on_amazon_pdf_done(self, out, report_out, total):
        self.last_pdf = out
        self.amazon_last_report = report_out
        try:
            self.amazon_generate_btn.config(state="normal")
        except Exception:
            pass
        self.status_var.set(f"Amazon PDF generated: {total} labels -> {out}")
        messagebox.showinfo("Amazon PDF generated", f"Amazon PDF generated successfully.\n\nLabels: {total}\nPDF:\n{out}\n\nReport CSV:\n{report_out}")

    def on_amazon_pdf_error(self, err):
        try:
            self.amazon_generate_btn.config(state="normal")
        except Exception:
            pass
        messagebox.showerror("Amazon PDF error", err)
        self.status_var.set("Amazon PDF generation failed. Check logs/debug_log.txt")

    def on_amazon_prn_done(self, out, report_out, total, print_after=False):
        self.last_prn = out
        self.amazon_last_report = report_out
        try:
            self.amazon_prn_btn.config(state="normal")
            if hasattr(self, "amazon_prn_print_btn"):
                self.amazon_prn_print_btn.config(state="normal")
        except Exception:
            pass
        self.status_var.set(f"Amazon PRN generated: {total} labels -> {out}")
        if print_after:
            self.print_last_prn_direct()
        else:
            messagebox.showinfo("Amazon PRN generated", f"Amazon PRN generated successfully.\n\nLabels: {total}\nPRN:\n{out}\n\nReport CSV:\n{report_out}")

    def on_amazon_prn_error(self, err):
        try:
            self.amazon_prn_btn.config(state="normal")
            if hasattr(self, "amazon_prn_print_btn"):
                self.amazon_prn_print_btn.config(state="normal")
        except Exception:
            pass
        messagebox.showerror("Amazon PRN error", err)
        self.status_var.set("Amazon PRN generation failed. Check logs/debug_log.txt")

    def show_empty_preview(self):
        self.preview.delete("all")
        self.preview.create_text(400, 260, text="Upload files to preview", fill="#777777", font=("Arial", 18, "bold"))
        if hasattr(self, "amazon_preview"):
            self.amazon_preview.delete("all")
            self.amazon_preview.create_text(30, 30, text="Upload Amazon consignment file to preview", anchor="nw", fill="#777777", font=("Arial", 16, "bold"))

    def preview_selected(self):
        idx = self.selected_index()
        if idx is None:
            messagebox.showwarning("No selection", "Select a file first.")
            return
        item = self.files[idx]
        df = item["df"]
        if len(df) == 0:
            return
        self.draw_canvas_label(item["format"], df, df.iloc[0], self.current_branch())
        self.status_var.set("Preview rendered. PDF uses the same text rules.")

    def draw_canvas_label(self, fmt, df, row, branch):
        c = self.preview
        c.delete("all")
        W = max(c.winfo_width(), 650)
        H = max(c.winfo_height(), 620)
        # Fit full 50x50 label inside preview. No right/bottom cutting.
        size = min(W - 60, H - 80)
        size = max(340, size)
        x0 = max(20, (W - size) / 2)
        y0 = 18
        scale = size / 49.8
        title, lines, lower = build_label_text(fmt, df, row, branch)
        barcode = get_barcode_value(df, row, branch)
        c.create_rectangle(x0, y0, x0 + size, y0 + size, fill="white", outline="black", width=2)
        title_font = min(30, max(17, int(2.55 * scale)))
        body_font = min(17, max(10, int(1.03 * scale)))
        small_font = min(15, max(9, int(0.83 * scale)))
        c.create_text(x0 + size / 2, y0 + 1.0 * scale, text=title, anchor="n", font=("Arial", title_font, "bold"))
        c.create_line(x0 + 3 * scale, y0 + 5.2 * scale, x0 + size - 3 * scale, y0 + 5.2 * scale, width=2)
        y = y0 + 6.4 * scale
        for line in lines:
            if line.startswith("Model Number:"):
                value = line.split(":", 1)[1].strip()
                if y <= y0 + 30.0 * scale:
                    c.create_text(x0 + 3.0 * scale, y, text="Model Number:", anchor="nw", font=("Arial", body_font, "bold"))
                    y += 1.25 * scale
                for part in wrap_text(value, 48):
                    if y > y0 + 30.0 * scale:
                        break
                    c.create_text(x0 + 4.2 * scale, y, text=part, anchor="nw", font=("Arial", small_font))
                    y += 1.20 * scale
                y += 0.12 * scale
                continue
            for j, part in enumerate(wrap_text(line, 52)):
                if y > y0 + 30.0 * scale:
                    break
                x_text = x0 + (3.0 if j == 0 else 4.4) * scale
                c.create_text(x_text, y, text=part, anchor="nw", font=("Arial", body_font))
                y += 1.25 * scale
            y += 0.10 * scale
        y = y0 + 31.2 * scale
        for i, line in enumerate(lower):
            font = ("Arial", small_font, "bold") if i == 0 else ("Arial", small_font)
            for part in wrap_text(line, 55):
                if y > y0 + 39.5 * scale:
                    break
                x_text = x0 + (3.0 if i == 0 else 4.0) * scale
                c.create_text(x_text, y, text=part, anchor="nw", font=font)
                y += 1.05 * scale
        bx0 = x0 + 6.2 * scale
        by0 = y0 + 41.1 * scale
        bw = 37.4 * scale
        bh = 4.7 * scale
        seed = sum(ord(ch) for ch in barcode)
        for i in range(120):
            if (i + seed) % 4 != 0:
                xx = bx0 + i * bw / 120
                c.create_line(xx, by0, xx, by0 + bh, width=1)
        c.create_text(x0 + size / 2, y0 + 46.25 * scale, text=barcode, anchor="n", font=("Arial", small_font))
        c.create_text(12, H - 18, text="Preview is screen-fitted. Final print uses V12 exact PDF: 106mm x 50mm 2UP roll, 3mm gap.", anchor="sw", fill="#555555", font=("Arial", 10))

    def validate_all(self):
        if not self.files:
            messagebox.showwarning("No files", "Upload files first.")
            return
        branch = self.current_branch()
        problems = []
        for item in self.files:
            df, fmt = item["df"], item["format"]
            missing = []
            if find_col(df, [branch.get("barcode_column", "FSN"), "FSN", "EAN", "LID"]) is None:
                missing.append("FSN/barcode column")
            if find_col(df, ["MRP", "mrp"]) is None:
                missing.append("MRP")
            for label, aliases in FORMATS[fmt]["fields"]:
                if find_col(df, aliases) is None:
                    missing.append(label)
            if missing:
                problems.append(f"{Path(item['path']).name}: missing {', '.join(missing)}")
        if problems:
            messagebox.showwarning("Validation issues", "\n".join(problems[:20]))
            self.status_var.set("Validation found issues.")
        else:
            messagebox.showinfo("Validation PASS", "All uploaded files passed basic validation.")
            self.status_var.set("Validation PASS.")

    def draw_pdf_label(self, c, x, y, w, h, fmt, df, row, branch):
        title, lines, lower = build_label_text(fmt, df, row, branch)
        barcode = get_barcode_value(df, row, branch)
        c.rect(x, y, w, h, stroke=1, fill=0)

        # V11: readable 50mm layout.
        # Goals: less blank space, bigger readable text, clean manufacturer block,
        # wider barcode, and no overlap between barcode/text/company details.
        title_font = 8.55
        body_font = 5.15
        model_font = 4.85
        lower_title_font = 4.65
        lower_font = 4.25

        c.setFont("Helvetica-Bold", title_font)
        c.drawCentredString(x + w / 2, y + h - 3.15 * mm, title)
        c.setLineWidth(0.55)
        c.line(x + 3 * mm, y + h - 5.30 * mm, x + w - 3 * mm, y + h - 5.30 * mm)

        # Bottom reserved areas
        barcode_y = y + 2.35 * mm
        barcode_h = 5.75 * mm
        barcode_text_y = y + 0.95 * mm
        barcode_top = barcode_y + barcode_h
        lower_limit = barcode_top + 0.85 * mm

        yy = y + h - 6.90 * mm
        # Product section can use space until just above company block.
        product_limit = y + 20.0 * mm

        # Slightly tighter wrap for model so it does not break awkwardly outside the label.
        for line in lines:
            if line.startswith("Model Number:"):
                value = line.split(":", 1)[1].strip()
                if yy >= product_limit:
                    c.setFont("Helvetica-Bold", body_font)
                    c.drawString(x + 3.0 * mm, yy, "Model Number:")
                    yy -= 1.70 * mm
                c.setFont("Helvetica", model_font)
                for part in wrap_text(value, 41):
                    if yy < product_limit:
                        break
                    c.drawString(x + 4.3 * mm, yy, part)
                    yy -= 1.60 * mm
                yy -= 0.15 * mm
                continue

            c.setFont("Helvetica", body_font)
            for j, part in enumerate(wrap_text(line, 45)):
                if yy < product_limit:
                    break
                c.drawString(x + (3.0 if j == 0 else 4.2) * mm, yy, part)
                yy -= 1.62 * mm
            yy -= 0.15 * mm

        # Company/manufacturer block: position it close to product text, but never into barcode.
        # This removes the big empty middle space and makes the label look balanced.
        lower_start = min(yy - 2.8 * mm, y + 16.55 * mm)
        lower_start = max(lower_start, y + 14.65 * mm)
        yy = lower_start

        for i, line in enumerate(lower):
            is_title = (i == 0)
            c.setFont("Helvetica-Bold" if is_title else "Helvetica", lower_title_font if is_title else lower_font)
            wrap_chars = 44 if is_title else 45
            indent = 3.0 if is_title else 4.2
            for part in wrap_text(line, wrap_chars):
                if yy < lower_limit:
                    break
                c.drawString(x + indent * mm, yy, part)
                yy -= (1.55 if is_title else 1.42) * mm
            if is_title:
                yy -= 0.18 * mm

        # Wider barcode, still kept inside border.
        if code128 is not None:
            try:
                target_w = w - 13.0 * mm
                bc = code128.Code128(barcode, barHeight=barcode_h, barWidth=0.22 * mm, humanReadable=False)
                if bc.width > target_w:
                    bw = bc.barWidth * (target_w / bc.width)
                    bc = code128.Code128(barcode, barHeight=barcode_h, barWidth=bw, humanReadable=False)
                bc.drawOn(c, x + (w - bc.width) / 2, barcode_y)
            except Exception:
                c.setFont("Helvetica", 4)
                c.drawCentredString(x + w / 2, y + 5.0 * mm, "BARCODE ERROR")
        c.setFont("Helvetica", 4.15)
        c.drawCentredString(x + w / 2, barcode_text_y, barcode)

    def total_print_labels(self):
        total = 0
        for item in self.files:
            for ridx, _r in item["df"].iterrows():
                total += get_row_qty(item, ridx)
        return total

    def generate_pdf_clicked(self):
        if not self.files:
            messagebox.showwarning("No files", "Upload files first.")
            return
        if pdfcanvas is None:
            messagebox.showerror("Missing package", "reportlab missing. Run install_requirements.bat.")
            return
        total = self.total_print_labels()
        if total > 20000:
            messagebox.showerror("Too many labels", f"You selected {total} labels. Please generate in smaller batches. Maximum 20,000 labels at once.")
            return
        if total > 2000:
            ok = messagebox.askyesno("Large PDF", f"You are generating {total} labels. This can take time and create a large PDF. Continue?")
            if not ok:
                return
        branch = copy.deepcopy(self.current_branch())
        layout = self.layout_var.get()
        files_snapshot = []
        for item in self.files:
            files_snapshot.append({"df": item["df"].copy(), "format": item["format"], "qty": dict(item.get("qty", {}))})
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = str(OUT_DIR / f"flipkart_labels_v12_{stamp}.pdf")
        try:
            self.generate_btn.config(state="disabled")
        except Exception:
            pass
        self.status_var.set(f"Generating {total} labels in background... app will stay usable.")
        self.update_idletasks()

        def worker():
            try:
                self.generate_pdf_worker(out, branch, layout, files_snapshot, total)
                self.after(0, lambda: self.on_pdf_done(out, total))
            except Exception as e:
                err = str(e)
                log(traceback.format_exc())
                self.after(0, lambda: self.on_pdf_error(err))

        threading.Thread(target=worker, daemon=True).start()

    def on_pdf_done(self, out, total):
        self.last_pdf = out
        try:
            self.generate_btn.config(state="normal")
        except Exception:
            pass
        self.status_var.set(f"PDF generated: {total} labels → {out}")
        messagebox.showinfo("PDF generated", f"PDF generated successfully.\n\nLabels: {total}\nV12 2UP roll size: 106mm x 50mm, middle gap 3mm.\nFile:\n{out}")

    def on_pdf_error(self, err):
        try:
            self.generate_btn.config(state="normal")
        except Exception:
            pass
        messagebox.showerror("PDF error", err)
        self.status_var.set("PDF generation failed. Check logs/debug_log.txt")

    def generate_pdf_worker(self, out, branch, layout, files_snapshot, total):
        # V12 exact measured 2UP roll support.
        # User measured roll total width 106mm, each label height 50mm, middle gap 3mm.
        # For 2-column roll PDF, one PDF page = one physical row of two labels.
        default_label_w_mm = safe_float(branch.get("roll_label_width_mm", "50.0"), 50.0)
        default_label_h_mm = safe_float(branch.get("roll_label_height_mm", "50.0"), 50.0)
        label_w = default_label_w_mm * mm
        label_h = default_label_h_mm * mm
        done = 0
        def qty_for(item, ridx):
            return safe_int(item.get("qty", {}).get(int(ridx), 1), 1)
        def progress():
            self.after(0, lambda d=done: self.status_var.set(f"Generating PDF... {d}/{total} labels done"))
        if layout == "2-column sticker roll":
            page_w_mm = safe_float(branch.get("roll_page_width_mm", "106.0"), 106.0)
            gap_x_mm = safe_float(branch.get("roll_gap_x_mm", "3.0"), 3.0)
            # Auto margin is calculated from measured roll width so labels sit centered: (106 - 50 - 3 - 50) / 2 = 1.5mm
            auto_margin_x_mm = max(0.0, (page_w_mm - (default_label_w_mm * 2) - gap_x_mm) / 2.0)
            margin_x_mm = safe_float(branch.get("roll_margin_x_mm", str(auto_margin_x_mm)), auto_margin_x_mm)
            margin_y_mm = safe_float(branch.get("roll_margin_y_mm", "0.0"), 0.0)
            rows_per_page = safe_int(branch.get("roll_rows_per_page", "1"), 1)
            if rows_per_page < 1:
                rows_per_page = 1
            gap_x = gap_x_mm * mm
            margin_x = margin_x_mm * mm
            margin_y = margin_y_mm * mm
            page_w = page_w_mm * mm
            page_h = (margin_y_mm * 2 + default_label_h_mm * rows_per_page) * mm
            c = pdfcanvas.Canvas(str(out), pagesize=(page_w, page_h), pageCompression=1)
            col = 0
            row_no = 0
            for item in files_snapshot:
                for ridx, r in item["df"].iterrows():
                    for _copy in range(qty_for(item, ridx)):
                        x = margin_x + col * (label_w + gap_x)
                        y = page_h - margin_y - (row_no + 1) * label_h
                        self.draw_pdf_label(c, x, y, label_w, label_h, item["format"], item["df"], r, branch)
                        done += 1
                        if done % 100 == 0:
                            progress()
                        col += 1
                        if col >= 2:
                            col = 0
                            row_no += 1
                        if row_no >= rows_per_page:
                            c.showPage()
                            col = 0
                            row_no = 0
            c.save()
        else:
            c = pdfcanvas.Canvas(str(out), pagesize=(label_w, label_h), pageCompression=1)
            for item in files_snapshot:
                for ridx, r in item["df"].iterrows():
                    for _copy in range(qty_for(item, ridx)):
                        self.draw_pdf_label(c, 0, 0, label_w, label_h, item["format"], item["df"], r, branch)
                        c.showPage()
                        done += 1
                        if done % 100 == 0:
                            progress()
            c.save()
        self.after(0, lambda: self.status_var.set(f"Saving PDF completed: {total}/{total} labels"))

    def generate_pdf(self):
        # Self-test/backward compatible direct generation.
        branch = self.current_branch()
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = str(OUT_DIR / f"flipkart_labels_v12_{stamp}.pdf")
        files_snapshot = [{"df": item["df"].copy(), "format": item["format"], "qty": dict(item.get("qty", {}))} for item in self.files]
        self.generate_pdf_worker(out, branch, self.layout_var.get(), files_snapshot, self.total_print_labels())
        return out

    def open_last_pdf(self):
        if not self.last_pdf or not os.path.exists(self.last_pdf):
            messagebox.showwarning("No PDF", "Generate PDF first.")
            return
        try:
            os.startfile(self.last_pdf)
        except Exception:
            subprocess.Popen([self.last_pdf], shell=True)

    def open_last_prn(self):
        if not self.last_prn or not os.path.exists(self.last_prn):
            messagebox.showwarning("No PRN", "Generate Amazon PRN first.")
            return
        try:
            os.startfile(self.last_prn)
        except Exception:
            subprocess.Popen([self.last_prn], shell=True)

    def print_last_pdf(self):
        if not self.last_pdf or not os.path.exists(self.last_pdf):
            messagebox.showwarning("No PDF", "Generate PDF first.")
            return
        try:
            os.startfile(self.last_pdf, "print")
            self.status_var.set("Print command sent. Use Actual Size / 100% / No Scaling.")
        except Exception as e:
            messagebox.showerror("Print error", f"Open PDF and press Ctrl+P.\n\n{e}")

    def print_last_prn_direct(self):
        if not self.last_prn or not os.path.exists(self.last_prn):
            messagebox.showwarning("No PRN", "Generate Amazon PRN first.")
            return
        try:
            import win32print
        except Exception:
            messagebox.showwarning(
                "pywin32 missing",
                "Install pywin32 or copy PRN manually to printer.\n\n"
                f'copy /b "{self.last_prn}" "\\\\COMPUTER\\TSC TE244"',
            )
            return
        printer_name = simpledialog.askstring("Raw PRN Print", "Printer share/name:", initialvalue="TSC TE244", parent=self)
        if not printer_name:
            return
        try:
            with open(self.last_prn, "rb") as f:
                data = f.read()
            handle = win32print.OpenPrinter(printer_name)
            try:
                job = win32print.StartDocPrinter(handle, 1, ("Amazon Labels PRN", None, "RAW"))
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, data)
                win32print.EndPagePrinter(handle)
                win32print.EndDocPrinter(handle)
            finally:
                win32print.ClosePrinter(handle)
            self.status_var.set(f"Raw PRN sent to {printer_name}.")
        except Exception as e:
            messagebox.showerror(
                "PRN print error",
                f"{e}\n\nFallback:\ncopy /b \"{self.last_prn}\" \"\\\\COMPUTER\\TSC TE244\"",
            )


def self_test():
    if pd is None or pdfcanvas is None:
        print("Missing packages. Run install_requirements.bat")
        return 1
    app_data = load_branches()
    branch = next(iter(app_data.values()))
    files = []
    for p in SAMPLE_DIR.glob("Quality_Check*.csv"):
        df = read_file(str(p))
        files.append((str(p), df, detect_format(str(p), df)))
    if not files:
        print("No sample files found")
        return 1
    label_w = label_h = 49.8 * mm
    out = OUT_DIR / "SELF_TEST_V12_sample_single_labels.pdf"
    c = pdfcanvas.Canvas(str(out), pagesize=(label_w, label_h))
    # local drawing without App instance
    def draw(c, x, y, w, h, fmt, df, row):
        title, lines, lower = build_label_text(fmt, df, row, branch)
        barcode = get_barcode_value(df, row, branch)
        c.rect(x, y, w, h, stroke=1, fill=0)
        c.setFont("Helvetica-Bold", 8.4); c.drawCentredString(x+w/2, y+h-5.4*mm, title)
        c.line(x+3*mm, y+h-9*mm, x+w-3*mm, y+h-9*mm)
        c.setFont("Helvetica", 4.55); yy=y+h-11.2*mm
        for line in lines:
            if line.startswith("Model Number:"):
                value = line.split(":", 1)[1].strip()
                if yy >= y+17*mm:
                    c.setFont("Helvetica-Bold", 4.45); c.drawString(x+3*mm, yy, "Model Number:"); yy -= 1.55*mm
                c.setFont("Helvetica", 4.15)
                for part in wrap_text(value, 58):
                    if yy < y+17*mm: break
                    c.drawString(x+4.6*mm, yy, part); yy -= 1.55*mm
                c.setFont("Helvetica", 4.55)
                continue
            for part in wrap_text(line, 62):
                if yy < y+17*mm: break
                c.drawString(x+3*mm, yy, part); yy -= 1.75*mm
        c.setFont("Helvetica", 4.25); yy=y+15.4*mm
        for i, line in enumerate(lower):
            c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 4.05)
            for part in wrap_text(line, 58):
                if yy < y+8.8*mm: break
                c.drawString(x+(3 if i == 0 else 4.4)*mm, yy, part); yy -= 1.35*mm
        bc = code128.Code128(barcode, barHeight=5.9*mm, barWidth=0.18*mm, humanReadable=False)
        bc.drawOn(c, x+(w-bc.width)/2, y+3.1*mm)
        c.setFont("Helvetica", 4.7); c.drawCentredString(x+w/2, y+1.55*mm, barcode)
    count = 0
    for _, df, fmt in files:
        for _, r in df.iterrows():
            draw(c, 0, 0, label_w, label_h, fmt, df, r)
            c.showPage(); count += 1
    c.save()
    print(f"SELF TEST Flipkart OK: generated {count} labels at {out}")

    separate_master = SAMPLE_DIR / "amazon_master.xlsx"
    separate_consignment = SAMPLE_DIR / "amazon_consignment.xlsx"
    amazon_sample = SAMPLE_DIR / "use it amazon.xlsx"
    if not amazon_sample.exists():
        amazon_sample = BASE_DIR / "use it amazon.xlsx"
    if separate_master.exists() and separate_consignment.exists():
        mapping = amazon_rules.load_mapping_settings()
        master = amazon_reader.load_master_listing_file(str(separate_master), mapping)
        consignment = amazon_reader.load_consignment_file(str(separate_consignment), mapping)
        amazon_rules.merge_sheet_options(consignment.get("sheet_categories", []), consignment.get("sheet_brands", []))
        rows = amazon_validation.resolve_amazon_rows(
            consignment["consignment_df"],
            mapping,
            amazon_rules.load_category_rules(),
            amazon_rules.load_brand_rules(),
            master_df=master["master_df"],
        )
        source_count = len(consignment["consignment_df"])
        test_mode = "separate files"
    elif amazon_sample.exists():
        mapping = amazon_rules.load_mapping_settings()
        workbook = amazon_reader.load_amazon_workbook(str(amazon_sample), mapping)
        amazon_rules.merge_sheet_options(workbook.get("sheet_categories", []), workbook.get("sheet_brands", []))
        rows = amazon_validation.resolve_amazon_rows(
            workbook,
            mapping,
            amazon_rules.load_category_rules(),
            amazon_rules.load_brand_rules(),
        )
        source_count = len(workbook["consignment_df"])
        test_mode = "combined workbook"
    else:
        rows = []
        source_count = 0
        test_mode = ""

    if rows:
        rows = [row for row in rows if row.get("merchant_sku") and row.get("fnsku") and row.get("main_heading") and row.get("brand")][:5]
        if not rows:
            print("SELF TEST Amazon failed: no usable rows found in sample workbook")
            return 1
        for row in rows:
            row["print_qty"] = 1
            if not row.get("mrp"):
                row["mrp"] = "799.00"
        amazon_validation.validate_amazon_rows(rows, branch)
        report_out = OUT_DIR / "SELF_TEST_amazon_label_report.csv"
        amazon_validation.write_report_csv(report_out, rows)
        errors = [f"{row.get('merchant_sku','')}: {'; '.join(row.get('errors', []))}" for row in rows if row.get("errors")]
        if errors:
            print("SELF TEST Amazon validation failed:")
            for err in errors[:10]:
                print("  " + err)
            print(f"Amazon validation report: {report_out}")
            return 1
        amazon_out = OUT_DIR / "SELF_TEST_amazon_labels.pdf"
        total_amazon = amazon_label_renderer.generate_amazon_pdf(amazon_out, rows, branch)
        prn_out = OUT_DIR / "SELF_TEST_amazon_labels.prn"
        total_prn = amazon_prn_renderer.generate_amazon_prn(prn_out, rows, branch)
        prn_text = prn_out.read_text(encoding="cp1252", errors="replace")
        if not prn_text.startswith("SIZE 101.5 mm, 50 mm"):
            print("SELF TEST Amazon PRN failed: missing SIZE header")
            return 1
        if "BARCODE" not in prn_text:
            print("SELF TEST Amazon PRN failed: missing BARCODE command")
            return 1
        if "PRINT" not in prn_text:
            print("SELF TEST Amazon PRN failed: missing PRINT command")
            return 1
        print(f"SELF TEST Amazon OK ({test_mode}): detected {source_count} row(s), generated {total_amazon} labels at {amazon_out}")
        print(f"SELF TEST Amazon PRN OK: generated {total_prn} labels at {prn_out}")
        print(f"SELF TEST Amazon report: {report_out}")
    else:
        print("SELF TEST Amazon skipped: samples/amazon_master.xlsx + samples/amazon_consignment.xlsx or samples/use it amazon.xlsx not found")
    return 0


def ui_smoke_test():
    app = App()
    app.update_idletasks()
    tabs = [app.main_notebook.tab(i, "text") for i in range(app.main_notebook.index("end"))]
    expected = ["Flipkart Labels", "Amazon Labels", "Branch / Address Settings", "Format / Mapping Settings"]
    missing = [tab for tab in expected if tab not in tabs]
    app.destroy()
    if missing:
        print(f"UI SMOKE TEST failed. Missing tabs: {missing}")
        return 1
    print("UI SMOKE TEST OK: Flipkart and Amazon tabs opened.")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--ui-smoke-test" in sys.argv:
        sys.exit(ui_smoke_test())
    try:
        app = App()
        app.mainloop()
    except Exception:
        log(traceback.format_exc())
        raise
