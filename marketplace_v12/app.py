import os
import sys
import json
import time
import traceback
import subprocess
import threading
import copy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.lib.units import mm
    from reportlab.graphics.barcode import code128, code39, code93
except Exception:
    pdfcanvas = None
    mm = 2.834645669291339
    code128 = None
    code39 = None
    code93 = None

try:
    from amazon_tool import AmazonLabelFrame
except ImportError:
    from marketplace_v12.amazon_tool import AmazonLabelFrame

APP_VERSION = "V12 Advanced - V24 Category PRN Templates"
APP_NAME = "M Men Style - Marketplace Label Generator V12 + Amazon"
BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
try:
    from output_manager import output_path as central_output_path, record_output, root_dir
except Exception:
    central_output_path = None
    def record_output(*args, **kwargs): return None
    def root_dir(): return Path.home() / "Desktop" / "MMS_Label_Tools_Output"
DATA_DIR = Path.home() / "Desktop" / "MMS_Label_Tools_Output" / "Database" / "marketplace_v12"
OUT_DIR = Path.home() / "Desktop" / "MMS_Label_Tools_Output" / "Marketplace_Product_Labels"
LOG_DIR = Path.home() / "Desktop" / "MMS_Label_Tools_Output" / "Logs"
SAMPLE_DIR = BASE_DIR / "samples"
for d in (DATA_DIR, OUT_DIR, LOG_DIR, SAMPLE_DIR):
    d.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "branches.json"
FORMATS_FILE = DATA_DIR / "label_formats.json"
PRN_PROFILES_FILE = DATA_DIR / "prn_category_profiles.json"
LOG_FILE = LOG_DIR / "debug_log.txt"

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
        "roll_rows_per_page": "1",
        "prn_layout_mode": "bartender_readable"
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


PRN_PROFILES = {
  "bangle_bracelet_armlet": {
    "title": "Bangle Bracelet Armlet",
    "right": {
      "title_x": 757,
      "title_y": 392,
      "text_x": 780,
      "barcode_x": 802,
      "barcode_y": 80,
      "code_x": 729,
      "code_y": 33
    },
    "left": {
      "title_x": 336,
      "title_y": 392,
      "text_x": 359,
      "barcode_x": 381,
      "barcode_y": 80,
      "code_x": 308,
      "code_y": 33
    },
    "barcode": {
      "type": "93",
      "height": 42,
      "readable": 0,
      "rotation": 180,
      "narrow": 2,
      "wide": 4
    },
    "source_prn": "Bracelet.prn"
  },
  "car_hanging_ornament": {
    "title": "Car_Hanging_Ornament",
    "right": {
      "title_x": 755,
      "title_y": 393,
      "text_x": 780,
      "barcode_x": 802,
      "barcode_y": 80,
      "code_x": 736,
      "code_y": 33
    },
    "left": {
      "title_x": 334,
      "title_y": 393,
      "text_x": 359,
      "barcode_x": 381,
      "barcode_y": 80,
      "code_x": 315,
      "code_y": 33
    },
    "barcode": {
      "type": "93",
      "height": 42,
      "readable": 0,
      "rotation": 180,
      "narrow": 2,
      "wide": 4
    },
    "source_prn": "flipkart car hanger prn.prn"
  },
  "car_hanger": {
    "alias_of": "car_hanging_ornament"
  },
  "earring": {
    "title": "Earring",
    "right": {
      "title_x": 661,
      "title_y": 392,
      "text_x": 789,
      "barcode_x": 802,
      "barcode_y": 80,
      "code_x": 740,
      "code_y": 33
    },
    "left": {
      "title_x": 240,
      "title_y": 392,
      "text_x": 368,
      "barcode_x": 381,
      "barcode_y": 80,
      "code_x": 319,
      "code_y": 33
    },
    "barcode": {
      "type": "93",
      "height": 42,
      "readable": 0,
      "rotation": 180,
      "narrow": 2,
      "wide": 4
    },
    "source_prn": "flipkart earring prn.prn"
  },
  "jewellery_set": {
    "title": "Jewellery Set",
    "right": {
      "title_x": 695,
      "title_y": 372,
      "text_x": 802,
      "barcode_x": 802,
      "barcode_y": 74,
      "code_x": 730,
      "code_y": 26
    },
    "left": {
      "title_x": 274,
      "title_y": 372,
      "text_x": 381,
      "barcode_x": 381,
      "barcode_y": 74,
      "code_x": 309,
      "code_y": 26
    },
    "barcode": {
      "type": "93",
      "height": 42,
      "readable": 0,
      "rotation": 180,
      "narrow": 2,
      "wide": 4
    },
    "source_prn": "flipkart jewellery set prn.prn"
  },
  "key_chain": {
    "title": "key chain",
    "right": {
      "title_x": 674,
      "title_y": 386,
      "text_x": 780,
      "barcode_x": 802,
      "barcode_y": 80,
      "code_x": 733,
      "code_y": 33
    },
    "left": {
      "title_x": 253,
      "title_y": 386,
      "text_x": 359,
      "barcode_x": 381,
      "barcode_y": 80,
      "code_x": 312,
      "code_y": 33
    },
    "barcode": {
      "type": "93",
      "height": 42,
      "readable": 0,
      "rotation": 180,
      "narrow": 2,
      "wide": 4
    },
    "source_prn": "flipkart keychain prn.prn"
  },
  "necklace_chain": {
    "title": "Necklace Chain",
    "right": {
      "title_x": 708,
      "title_y": 386,
      "text_x": 780,
      "barcode_x": 802,
      "barcode_y": 80,
      "code_x": 738,
      "code_y": 33
    },
    "left": {
      "title_x": 287,
      "title_y": 386,
      "text_x": 359,
      "barcode_x": 381,
      "barcode_y": 80,
      "code_x": 317,
      "code_y": 33
    },
    "barcode": {
      "type": "93",
      "height": 42,
      "readable": 0,
      "rotation": 180,
      "narrow": 2,
      "wide": 4
    },
    "source_prn": "flipkart necklace chain prn.prn"
  },
  "pendant_locket": {
    "title": "Pendant Locket",
    "right": {
      "title_x": 707,
      "title_y": 392,
      "text_x": 780,
      "barcode_x": 802,
      "barcode_y": 74,
      "code_x": 726,
      "code_y": 26
    },
    "left": {
      "title_x": 286,
      "title_y": 392,
      "text_x": 359,
      "barcode_x": 381,
      "barcode_y": 74,
      "code_x": 305,
      "code_y": 26
    },
    "barcode": {
      "type": "93",
      "height": 42,
      "readable": 0,
      "rotation": 180,
      "narrow": 2,
      "wide": 4
    },
    "source_prn": "flipkart pendant prn.prn"
  },
  "ring": {
    "title": "Ring",
    "right": {
      "title_x": 647,
      "title_y": 387,
      "text_x": 789,
      "barcode_x": 802,
      "barcode_y": 74,
      "code_x": 739,
      "code_y": 26
    },
    "left": {
      "title_x": 226,
      "title_y": 387,
      "text_x": 368,
      "barcode_x": 381,
      "barcode_y": 74,
      "code_x": 318,
      "code_y": 26
    },
    "barcode": {
      "type": "93",
      "height": 42,
      "readable": 0,
      "rotation": 180,
      "narrow": 2,
      "wide": 4
    },
    "source_prn": "flipkart ring prn.prn"
  }
}


def _resolve_prn_profile(fmt_key):
    prof = PRN_PROFILES.get(fmt_key) or PRN_PROFILES.get("key_chain", {})
    if isinstance(prof, dict) and prof.get("alias_of"):
        prof = PRN_PROFILES.get(prof.get("alias_of"), PRN_PROFILES.get("key_chain", {}))
    return prof


def save_prn_profiles(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PRN_PROFILES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_prn_profiles():
    global PRN_PROFILES
    try:
        if PRN_PROFILES_FILE.exists():
            data = json.loads(PRN_PROFILES_FILE.read_text(encoding="utf-8"))
            if data:
                # Merge new built-in categories into existing user database without deleting user edits.
                changed = False
                for k, v in PRN_PROFILES.items():
                    if k not in data:
                        data[k] = v
                        changed = True
                PRN_PROFILES = data
                if changed:
                    save_prn_profiles(PRN_PROFILES)
                return
    except Exception:
        log(traceback.format_exc())
    save_prn_profiles(PRN_PROFILES)


def save_formats(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
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
                # Merge new built-in formats into existing user database without deleting user mappings.
                changed = False
                for k, v in FORMATS.items():
                    if k not in data:
                        data[k] = v
                        changed = True
                FORMATS = data
                if changed:
                    save_formats(FORMATS)
                return
    except Exception:
        log(traceback.format_exc())
    save_formats(FORMATS)



def log(msg):
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " | " + str(msg) + "\n")
    except Exception:
        pass


load_formats()
load_prn_profiles()

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
        return "car_hanging_ornament"
    if "showpiece" in name or "figurine" in name:
        return "showpiece_figurine"
    if "brooch" in name:
        return "brooch"
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
    if "model_name" in cols and "color" in cols:
        return "car_hanging_ornament"
    if "model_id" in cols:
        return "brooch"
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
    DATA_DIR.mkdir(parents=True, exist_ok=True)
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


class App(tk.Frame):
    def __init__(self, master=None, embedded=False, on_back=None):
        self._standalone = master is None
        self.root_window = tk.Tk() if master is None else master
        super().__init__(self.root_window)
        self.embedded = embedded
        self.on_back = on_back
        if self._standalone:
            self.pack(fill="both", expand=True)
        root = self.winfo_toplevel()
        try: root.title(APP_NAME)
        except Exception: pass
        try: root.geometry("1450x850")
        except Exception: pass
        try: root.minsize(1100, 700)
        except Exception: pass
        self.branches = load_branches()
        self.files = []
        self.last_pdf = ""
        self.last_prn = ""
        self.selected_printer = self.load_selected_printer()
        self._auto_print_after_prn = False
        self.status_var = tk.StringVar(value="Ready")
        self.row_qty_var = tk.StringVar(value="1")
        self.change_format_var = tk.StringVar()
        self.prn_mode_var = tk.StringVar(value="bartender_readable")
        self.build_ui()
        self.refresh_branches()
        self.show_empty_preview()
        log("App started")

    def _apply_dark_style(self, style):
        BG="#0F0F1A"; PANEL="#16162A"; CARD="#1E1E32"; BORDER="#2A2A48"; TEXT="#F4F1E8"; MUTED="#A5A5B8"; ACCENT="#C8A96E"
        try:
            style.configure("TFrame", background=PANEL)
            style.configure("TNotebook", background=BG, borderwidth=0)
            style.configure("TNotebook.Tab", background=CARD, foreground=MUTED, padding=(16, 8), font=("Segoe UI", 9, "bold"))
            style.map("TNotebook.Tab", background=[("selected", PANEL)], foreground=[("selected", ACCENT)])
            style.configure("TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 9))
            style.configure("TButton", background=CARD, foreground=TEXT, padding=(10, 6), font=("Segoe UI", 9, "bold"))
            style.map("TButton", background=[("active", ACCENT)], foreground=[("active", "#111111")])
            style.configure("TEntry", fieldbackground=CARD, foreground=TEXT, insertcolor=TEXT)
            style.configure("TCombobox", fieldbackground=CARD, background=CARD, foreground=TEXT, arrowcolor=ACCENT)
            style.configure("Treeview", background=CARD, foreground=TEXT, fieldbackground=CARD, rowheight=24, bordercolor=BORDER)
            style.configure("Treeview.Heading", background=PANEL, foreground=ACCENT, font=("Segoe UI", 9, "bold"))
            style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#111111")])
        except Exception:
            pass

    def build_ui(self):
        self.configure(bg="#0F0F1A")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        self._apply_dark_style(style)
        topbar = tk.Frame(self, bg="#16162A", height=62)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        tk.Frame(topbar, bg="#C8A96E", width=5).pack(side="left", fill="y")
        if self.on_back:
            tk.Button(topbar, text="← Back", command=self.on_back, bg="#1E1E32", fg="#F4F1E8",
                      activebackground="#C8A96E", activeforeground="#111111", relief="flat",
                      padx=12, pady=7, cursor="hand2", font=("Segoe UI", 9, "bold")).pack(side="left", padx=14, pady=14)
        tk.Label(topbar, text="MARKETPLACE PRODUCT LABEL GENERATOR V12 + AMAZON", bg="#16162A", fg="#F4F1E8",
                 font=("Segoe UI", 17, "bold")).pack(side="left", padx=12)
        tk.Label(topbar, text="2-up thermal labels • Multiple Excel/CSV files • Central Desktop output", bg="#16162A",
                 fg="#A5A5B8", font=("Segoe UI", 9)).pack(side="left", padx=16)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=12)
        self.tab_gen = ttk.Frame(nb)
        self.tab_amazon = ttk.Frame(nb)
        self.tab_set = ttk.Frame(nb)
        self.tab_map = ttk.Frame(nb)
        nb.add(self.tab_gen, text="Generate Labels")
        nb.add(self.tab_amazon, text="Amazon Labels")
        nb.add(self.tab_set, text="Branches & Settings")
        nb.add(self.tab_map, text="Format Mapping")

        self.amazon_tool = AmazonLabelFrame(
            self.tab_amazon,
            branches_provider=lambda: self.branches,
            current_branch_provider=lambda: self.current_branch() if hasattr(self, "current_branch") else None
        )
        self.amazon_tool.pack(fill="both", expand=True)

        # Organized action panel: buttons are split into rows so they stay visible on smaller screens.
        toolbar = ttk.Frame(self.tab_gen)
        toolbar.pack(fill="x", padx=4, pady=(4, 2))

        action_row = ttk.Frame(toolbar)
        action_row.pack(fill="x", pady=2)
        ttk.Label(action_row, text="1) Files:").pack(side="left", padx=(0, 4))
        ttk.Button(action_row, text="Upload Files", command=self.upload_files).pack(side="left", padx=3)
        ttk.Button(action_row, text="Clear", command=self.clear_files).pack(side="left", padx=3)
        ttk.Button(action_row, text="Preview", command=self.preview_selected).pack(side="left", padx=(12, 3))
        ttk.Button(action_row, text="Validate", command=self.validate_all).pack(side="left", padx=3)

        print_row = ttk.Frame(toolbar)
        print_row.pack(fill="x", pady=2)
        ttk.Label(print_row, text="2) Print:").pack(side="left", padx=(0, 4))
        self.generate_prn_btn = ttk.Button(print_row, text="Generate PRN", command=self.generate_prn_clicked)
        self.generate_prn_btn.pack(side="left", padx=3)
        ttk.Button(print_row, text="Generate PRN & Print", command=lambda: self.generate_prn_clicked(auto_print=True)).pack(side="left", padx=3)
        ttk.Button(print_row, text="Select Printer", command=self.select_printer_dialog).pack(side="left", padx=3)
        ttk.Button(print_row, text="Print Last PRN", command=self.print_last_prn).pack(side="left", padx=3)
        ttk.Button(print_row, text="Open PRN Folder", command=self.open_last_prn_folder).pack(side="left", padx=3)
        self.generate_btn = ttk.Button(print_row, text="PDF Preview", command=self.generate_pdf_clicked)
        self.generate_btn.pack(side="left", padx=(14, 3))
        ttk.Button(print_row, text="Open PDF", command=self.open_last_pdf).pack(side="left", padx=3)

        setting_row = ttk.Frame(toolbar)
        setting_row.pack(fill="x", pady=2)
        ttk.Label(setting_row, text="Branch:").pack(side="left", padx=(0, 4))
        self.branch_var = tk.StringVar()
        self.branch_combo = ttk.Combobox(setting_row, textvariable=self.branch_var, state="readonly", width=20)
        self.branch_combo.pack(side="left")
        self.branch_combo.bind("<<ComboboxSelected>>", self.on_main_branch_changed)
        ttk.Label(setting_row, text="PDF Layout:").pack(side="left", padx=(14, 4))
        self.layout_var = tk.StringVar(value="2-column sticker roll")
        self.layout_combo = ttk.Combobox(setting_row, textvariable=self.layout_var, state="readonly", width=20, values=["Single label pages", "2-column sticker roll"])
        self.layout_combo.pack(side="left")
        ttk.Label(setting_row, text="Format:").pack(side="left", padx=(14, 4))
        self.change_format_combo = ttk.Combobox(setting_row, textvariable=self.change_format_var, state="readonly", width=20)
        self.change_format_combo.pack(side="left")
        ttk.Button(setting_row, text="Apply Format", command=self.apply_selected_format).pack(side="left", padx=4)

        prn_row = ttk.Frame(toolbar)
        prn_row.pack(fill="x", pady=2)
        ttk.Label(prn_row, text="3) PRN Print Mode:").pack(side="left", padx=(0, 4))
        self.prn_mode_combo = ttk.Combobox(prn_row, textvariable=self.prn_mode_var, state="readonly", width=24,
                                           values=["bartender_readable", "full_info_compact"])
        self.prn_mode_combo.pack(side="left", padx=3)
        self.prn_mode_combo.bind("<<ComboboxSelected>>", self.update_current_branch_prn_mode)
        ttk.Label(prn_row, text="Use bartender_readable for daily clear 50mm printing. PDF is preview only; PRN is final print.").pack(side="left", padx=10)

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
        ttk.Label(qtybar, text="Print Qty selected SKU:").pack(side="left")
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
        ttk.Label(footer, text="Print rule: For scanning use PRN / Direct Print. PDF is preview only.").pack(side="right")
        self.build_settings_tab()
        self.build_format_tab()

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
            ("prn_layout_mode", "PRN Layout Mode (bartender_readable / full_info_compact)"),
        ]
        for i, (key, label) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=5)
            ent = ttk.Entry(form, width=115)
            ent.grid(row=i, column=1, sticky="ew", padx=5, pady=5)
            self.entry[key] = ent
        form.columnconfigure(1, weight=1)
        ttk.Label(self.tab_set, text="For bartender_readable PRN, keep address short. Customer Care and Email are printed from these Branch Settings.").pack(anchor="w", padx=14, pady=8)

    def build_format_tab(self):
        top = ttk.Frame(self.tab_map)
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
        ttk.Label(self.tab_map, text=help_text, justify="left").pack(anchor="w", padx=14, pady=6)
        form = ttk.Frame(self.tab_map)
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
        if self.branch_var.get() not in names:
            self.branch_var.set(names[0])
        if self.settings_branch_var.get() not in names:
            self.settings_branch_var.set(names[0])
        try:
            if hasattr(self, "amazon_tool"):
                self.amazon_tool.refresh_branch_list()
        except Exception:
            pass
        self.on_main_branch_changed()
        self.load_branch_form()

    def current_branch(self):
        b = self.branches.get(self.branch_var.get()) or next(iter(self.branches.values()))
        # The toolbar PRN mode is treated as the active print mode for Tool 2.
        # It is also saved into Branch Settings when changed, but this keeps generation safe
        # even if the user changes the dropdown and prints immediately.
        try:
            mode = (self.prn_mode_var.get() or "bartender_readable").strip()
            if mode in ("bartender_readable", "full_info_compact"):
                b = dict(b)
                b["prn_layout_mode"] = mode
        except Exception:
            pass
        return b

    def on_main_branch_changed(self, event=None):
        b = self.branches.get(self.branch_var.get(), {})
        mode = (b.get("prn_layout_mode") or "bartender_readable").strip()
        if mode not in ("bartender_readable", "full_info_compact"):
            mode = "bartender_readable"
        try:
            self.prn_mode_var.set(mode)
        except Exception:
            pass

    def update_current_branch_prn_mode(self, event=None):
        mode = (self.prn_mode_var.get() or "bartender_readable").strip()
        if mode not in ("bartender_readable", "full_info_compact"):
            mode = "bartender_readable"
            self.prn_mode_var.set(mode)
        name = self.branch_var.get()
        if name in self.branches:
            self.branches[name]["prn_layout_mode"] = mode
            try:
                save_branches(self.branches)
            except Exception:
                pass
            # Keep settings tab in sync when editing the same branch.
            try:
                if self.settings_branch_var.get() == name and "prn_layout_mode" in self.entry:
                    self.entry["prn_layout_mode"].delete(0, "end")
                    self.entry["prn_layout_mode"].insert(0, mode)
            except Exception:
                pass
        self.status_var.set(f"PRN layout mode set to: {mode}")

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
        try:
            if name == self.branch_var.get():
                mode = (data.get("prn_layout_mode") or "bartender_readable").strip()
                if mode not in ("bartender_readable", "full_info_compact"):
                    mode = "bartender_readable"
                self.prn_mode_var.set(mode)
        except Exception:
            pass
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

    def show_empty_preview(self):
        self.preview.delete("all")
        self.preview.create_text(400, 260, text="Upload files to preview", fill="#777777", font=("Arial", 18, "bold"))

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
        """V19 PDF preview/export layout.
        PDF is only preview/export; real barcode printing should use PRN.
        This version fixes text overwrite by using fixed zones and smaller line-safe fonts.
        """
        title, lines, lower = build_label_text(fmt, df, row, branch)
        barcode = clean_val(get_barcode_value(df, row, branch)).upper()

        c.setLineWidth(0.42)
        c.rect(x + 0.45 * mm, y + 0.45 * mm, w - 0.90 * mm, h - 0.90 * mm, stroke=1, fill=0)

        left = x + 1.45 * mm
        right = x + w - 1.45 * mm
        usable_w = right - left

        def fit_font(text, font_name, max_size, min_size, max_width):
            text = str(text)
            size = max_size
            while size > min_size and c.stringWidth(text, font_name, size) > max_width:
                size -= 0.15
            return max(size, min_size)

        def wrap_by_width(text, font_name, font_size, max_width, max_lines=99):
            text = clean_val(text)
            if not text:
                return []
            words = text.split()
            out, cur = [], ''
            for word in words:
                test = (cur + ' ' + word).strip()
                if not cur or c.stringWidth(test, font_name, font_size) <= max_width:
                    cur = test
                else:
                    out.append(cur)
                    cur = word
                    if len(out) >= max_lines:
                        break
            if cur and len(out) < max_lines:
                out.append(cur)
            return out[:max_lines]

        # Zones in mm from bottom.
        title_top_y = y + h - 3.95 * mm
        product_start = y + h - 7.15 * mm
        product_stop = y + 22.0 * mm
        lower_start_max = y + 20.0 * mm   # V20: reduce middle gap safely
        lower_stop = y + 10.5 * mm
        barcode_text_y = y + 1.0 * mm
        barcode_y = y + 3.05 * mm
        barcode_h = 5.25 * mm
        barcode_zone_top = y + 9.5 * mm

        # White barcode zone, so text never runs inside it.
        c.setFillColorRGB(1, 1, 1)
        c.rect(x + 0.8*mm, y + 0.8*mm, w - 1.6*mm, barcode_zone_top - y - 0.45*mm, stroke=0, fill=1)
        c.setFillColorRGB(0, 0, 0)

        # Title
        title = clean_val(title).replace('_', ' ')
        title_font = fit_font(title, 'Helvetica-Bold', 9.5, 7.3, usable_w)
        c.setFont('Helvetica-Bold', title_font)
        c.drawCentredString(x + w/2, title_top_y, title)
        c.setLineWidth(0.30)
        c.line(left, y + h - 5.65*mm, right, y + h - 5.65*mm)

        # Product details with safe spacing.
        yy = product_start
        field_font = 4.30
        value_font = 4.22
        small_font = 3.98
        line_gap = 1.48 * mm

        for raw in lines:
            raw = clean_val(raw)
            if not raw or yy < product_stop:
                break
            if ':' in raw:
                key, val = raw.split(':', 1)
                key, val = key.strip(), val.strip()
                label_txt = f'{key}:'
                c.setFont('Helvetica-Bold', field_font)
                c.drawString(left, yy, label_txt)
                lx = left + c.stringWidth(label_txt + ' ', 'Helvetica-Bold', field_font)
                max_val_w = right - lx
                if key.lower().startswith('model number'):
                    yy -= line_gap
                    for part in wrap_by_width(val, 'Helvetica-Bold', small_font, usable_w - 0.6*mm, max_lines=2):
                        if yy < product_stop: break
                        c.setFont('Helvetica-Bold', small_font)
                        c.drawString(left + 0.65*mm, yy, part)
                        yy -= line_gap
                    continue
                if c.stringWidth(val, 'Helvetica-Bold', value_font) <= max_val_w:
                    c.setFont('Helvetica-Bold', value_font)
                    c.drawString(lx, yy, val)
                    yy -= line_gap
                else:
                    parts = wrap_by_width(val, 'Helvetica-Bold', small_font, usable_w - 0.6*mm, max_lines=2)
                    first = True
                    for part in parts:
                        if yy < product_stop: break
                        c.setFont('Helvetica-Bold', small_font)
                        if first and c.stringWidth(part, 'Helvetica-Bold', small_font) <= max_val_w:
                            c.drawString(lx, yy, part)
                        else:
                            c.drawString(left + 0.65*mm, yy, part)
                        yy -= line_gap
                        first = False
            else:
                for part in wrap_by_width(raw, 'Helvetica-Bold', value_font, usable_w, max_lines=2):
                    if yy < product_stop: break
                    c.setFont('Helvetica-Bold', value_font)
                    c.drawString(left, yy, part)
                    yy -= line_gap

        # Lower manufacturer/customer-care block with proper spacing.
        yy = min(yy - 0.8*mm, lower_start_max)
        yy = max(yy, y + 18.4*mm)  # V20: keep lower block closer, but still safe
        lower_heading_font = 4.65
        lower_font = 3.95
        lower_gap = 1.32 * mm
        for i, raw in enumerate(lower):
            raw = clean_val(raw)
            if not raw or yy < lower_stop:
                break
            if i == 0:
                fs = fit_font(raw, 'Helvetica-Bold', lower_heading_font, 3.95, usable_w)
                c.setFont('Helvetica-Bold', fs)
                c.drawString(left, yy, raw)
                c.setLineWidth(0.22)
                c.line(left, yy - 0.25*mm, min(right, left + c.stringWidth(raw, 'Helvetica-Bold', fs)), yy - 0.25*mm)
                yy -= lower_gap
            else:
                for part in wrap_by_width(raw, 'Helvetica-Bold', lower_font, usable_w, max_lines=1):
                    if yy < lower_stop: break
                    c.setFont('Helvetica-Bold', lower_font)
                    c.drawString(left + 0.5*mm, yy, part)
                    yy -= lower_gap

        # PDF barcode preview. Real printing uses PRN, but keep this close to BarTender.
        rendered = False
        try:
            allowed39 = set('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%')
            if code39 is not None and barcode and all(ch in allowed39 for ch in barcode):
                bc = code39.Standard39(barcode, barWidth=0.18*mm, barHeight=barcode_h, checksum=0, stop=1, humanReadable=False, quiet=0)
                target_w = w - 4.2*mm
                if bc.width > target_w:
                    bw = max(0.14*mm, bc.barWidth * (target_w / bc.width))
                    bc = code39.Standard39(barcode, barWidth=bw, barHeight=barcode_h, checksum=0, stop=1, humanReadable=False, quiet=0)
                bc.drawOn(c, x + (w-bc.width)/2, barcode_y)
                rendered = True
        except Exception:
            rendered = False
        if not rendered:
            c.setFont('Helvetica-Bold', 4.2)
            c.drawCentredString(x+w/2, y+4.6*mm, 'BARCODE PREVIEW')
        code_font = fit_font(barcode, 'Helvetica-Bold', 4.95, 3.85, w - 3.2*mm)
        c.setFont('Helvetica-Bold', code_font)
        c.drawCentredString(x + w/2, barcode_text_y, barcode)


    # ─────────────────────────────────────────────────────────────
    # Native TSPL/PRN output based on user's real working BarTender PRN
    # Real PRN findings:
    #   SIZE 101.5 mm, 50 mm | GAP 3 mm | SPEED 3 | DENSITY 10
    #   Barcode: Code39, height 37 dots, rotation 180, narrow/wide 1/3
    # This is preferred for actual thermal barcode printing.

    def _tspl_clean(self, value, max_len=120):
        value = str(value or "")
        value = value.replace('₹', 'Rs.').replace('–', '-').replace('—', '-')
        value = value.replace('“', '"').replace('”', '"').replace('’', "'")
        value = value.replace('"', "'")
        value = value.replace('\r', ' ').replace('\n', ' ')
        value = ' '.join(value.split())
        try:
            value.encode('ascii')
        except Exception:
            value = value.encode('ascii', 'ignore').decode('ascii')
        return value[:max_len]

    def _code39_clean(self, value):
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-. $/+%")
        value = self._tspl_clean(value, 60).upper()
        value = ''.join(ch if ch in allowed else '-' for ch in value)
        return value or "NO-BARCODE"

    def _wrap_chars(self, text, limit=45, max_lines=2):
        text = self._tspl_clean(text, 200)
        words = text.split()
        lines, cur = [], ""
        for word in words:
            test = (cur + " " + word).strip()
            if len(test) <= limit:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = word[:limit]
                if len(lines) >= max_lines:
                    break
        if cur and len(lines) < max_lines:
            lines.append(cur)
        return (lines + [""] * max_lines)[:max_lines]

    def _field_dict_from_lines(self, lines):
        d = {}
        for raw in lines:
            if ':' in str(raw):
                k, v = str(raw).split(':', 1)
                key = ''.join(ch.lower() for ch in k if ch.isalnum())
                d[key] = v.strip()
        return d

    def _prn_text(self, x, y, font, rot, xm, ym, text):
        return f'TEXT {x},{y},"{font}",{rot},{xm},{ym},"{self._tspl_clean(text)}"'

    def _prn_barcode(self, x, y, code, fmt=None):
        # V24: barcode is taken from the matching uploaded BarTender PRN profile.
        # Do not change these values unless you intentionally change the physical BarTender template.
        prof = _resolve_prn_profile(fmt or "key_chain")
        bc = prof.get("barcode", {}) if isinstance(prof, dict) else {}
        btype = bc.get("type", "93")
        height = int(bc.get("height", 42))
        readable = int(bc.get("readable", 0))
        rotation = int(bc.get("rotation", 180))
        narrow = int(bc.get("narrow", 2))
        wide = int(bc.get("wide", 4))
        return f'BARCODE {x},{y},"{btype}",{height},{readable},{rotation},{narrow},{wide},"{self._code39_clean(code)}"'

    def _make_prn_label_lines(self, slot, fmt, df, row, branch):
        """Create one 50mm label in native TSPL.

        V21 important change:
        PRN is now the source-of-truth for actual printing. The default
        `bartender_readable` mode follows the working BarTender PRN more closely:
        font multipliers, Y spacing, barcode position, and barcode text size are
        restored to the proven values. This avoids the tiny-text problem caused
        by trying to force too many fields into 50mm.

        If you need every legal/address line, set branch setting
        prn_layout_mode = full_info_compact, but for real readable barcode label
        printing, bartender_readable is recommended.
        """
        prof = _resolve_prn_profile(fmt)
        side = prof.get(slot, {}) if isinstance(prof, dict) else {}
        if slot == 'right':
            title_x = int(side.get('title_x', 697)); title_y = int(side.get('title_y', 392))
            text_x = int(side.get('text_x', 780)); barcode_x = int(side.get('barcode_x', 802))
            barcode_y = int(side.get('barcode_y', 80)); code_x = int(side.get('code_x', 733)); code_y = int(side.get('code_y', 33))
        else:
            title_x = int(side.get('title_x', 286)); title_y = int(side.get('title_y', 392))
            text_x = int(side.get('text_x', 359)); barcode_x = int(side.get('barcode_x', 381))
            barcode_y = int(side.get('barcode_y', 80)); code_x = int(side.get('code_x', 312)); code_y = int(side.get('code_y', 33))

        title, top_lines, lower = build_label_text(fmt, df, row, branch)
        fields = self._field_dict_from_lines(top_lines)
        cfg = FORMATS.get(fmt, FORMATS.get('key_chain', {}))
        mode = (branch.get('prn_layout_mode') or 'bartender_readable').strip().lower()

        brand = fields.get('brand') or row_value(df, row, ['Brand', 'brand'], '') or 'M Men Style'
        model = fields.get('modelnumber') or row_value(df, row, ['model_number', 'model no', 'model', 'Model Number'], '')
        plating = fields.get('plating') or row_value(df, row, ['plating'], '')
        color = fields.get('brandcolor') or fields.get('color') or row_value(df, row, ['brand_color', 'color'], '')
        material = fields.get('bodymaterial') or fields.get('material') or row_value(df, row, ['body_material', 'material'], '')
        net_qty = fields.get('netquantity') or '1 N'
        dimensions = fields.get('dimensions') or branch.get('dimension', '85mm*70mm*8mm')
        month_year = branch.get('month_year', 'May 2026')
        mrp_raw = row_value(df, row, ['MRP', 'mrp'], '')
        if mrp_raw:
            mrp = f"Rs.{self._tspl_clean(mrp_raw)}.00 (inclusive of all Taxes)"
        else:
            mrp = 'Rs.799.00 (inclusive of all Taxes)'
        generic = cfg.get('generic', title)
        barcode = self._code39_clean(get_barcode_value(df, row, branch))

        lines = []
        # Working BarTender title values: font 0, x/y multiplier 9/10.
        lines.append(self._prn_text(title_x, title_y, '0', 180, 9, 10, title))

        if mode == 'full_info_compact':
            # Compact mode keeps address/customer care but text becomes smaller.
            model_1, model_2 = self._wrap_chars(model, limit=43, max_lines=2)
            product_y = [352, 337, 322, 307, 292, 277, 262, 247, 232, 217, 202]
            product_lines = [
                f'Brand              : {brand}',
                f'Model Number :{model_1}',
                model_2 if model_2 else '',
                f'Plating             : {plating}',
                f'Brand Color     : {color}',
                f'Body Material  : {material}',
                f'Net Quantity   : {net_qty}',
                f'Dimensions - {dimensions}',
                f'MRP     : {mrp}',
                f'Generic Name  : {generic}',
                f'Month & Year of Mfg: {month_year}',
            ]
            for yy, txt in zip(product_y, product_lines):
                if txt:
                    lines.append(self._prn_text(text_x, yy, 'ROMAN.TTF', 180, 1, 4, self._tspl_clean(txt, 58)))
            lower_lines = [
                'Manufactured by / Marketed by:',
                branch.get('marketed_by', 'Sujal Fashion Works, Shop No F-10,'),
                branch.get('address', 'Amranate, Sec-09E, Kalamboli, Navi Mumbai'),
                f"Email: {branch.get('email', 'Sujalfashionworks@gmail.com')}",
                f"Contact: {branch.get('phone', '+91-9594790929')}",
                f"{branch.get('origin', 'Country of Origin: India')} | Mfg: {month_year}",
            ]
            for yy, txt in zip([190, 176, 162, 148, 134, 120], lower_lines):
                lines.append(self._prn_text(text_x, yy, 'ROMAN.TTF', 180, 1, 3, self._tspl_clean(txt, 58)))
        else:
            # Recommended readable mode: daily production mode.
            # Goal: readable text + customer care/email + no overlap + same scanning barcode.
            # Keep only the product lines that fit clearly; extra format fields are skipped safely.
            # V23: keep product text readable but reserve enough area for a bold lower block.
            # Using the same ROMAN.TTF multiplier 1,5 style as the working BarTender PRN.
            product_y = [351, 335, 319, 303, 287, 271, 255, 239, 223]
            product_lines = []

            for label, aliases in cfg.get('fields', []):
                val = row_value(df, row, aliases, '')
                if not val:
                    continue
                if label.lower().startswith('model'):
                    m1, m2 = self._wrap_chars(val, limit=43, max_lines=2)
                    product_lines.append(f'Model Number :{m1}')
                    if m2:
                        product_lines.append(m2)
                else:
                    product_lines.append(f'{label:<18}: {self._tspl_clean(val, 48)}')
                if len(product_lines) >= len(product_y):
                    break

            existing = ' '.join(product_lines).lower()
            priority_lines = []
            if 'brand' not in existing:
                priority_lines.append(f'Brand              : {brand}')
            if 'net quantity' not in existing:
                priority_lines.append(f'Net Quantity   : {net_qty}')
            if 'mrp' not in existing:
                priority_lines.append(f'MRP     : {mrp}')
            if 'generic' not in existing:
                priority_lines.append(f'Generic Name  : {generic}')
            priority_lines.append(f'Month & Year of Mfg: {month_year}')

            for txt in priority_lines:
                if len(product_lines) >= len(product_y):
                    break
                product_lines.append(txt)

            for yy, txt in zip(product_y, product_lines):
                lines.append(self._prn_text(text_x, yy, 'ROMAN.TTF', 180, 1, 5, self._tspl_clean(txt, 58)))

            # Lower readable compliance/contact block. It prints from Branch Settings,
            # so future branches can use shorter addresses without code changes.
            address_lines = self._wrap_chars(branch.get('address', 'Amranate, Sec-09E, Kalamboli, Navi Mumbai'), limit=42, max_lines=2)
            lower_lines = [
                'Manufactured by / Marketed by:',
                branch.get('marketed_by', 'Sujal Fashion Works, Shop No F-10,'),
            ]
            lower_lines.extend([ln for ln in address_lines if ln])
            lower_lines.extend([
                f"Customer Care: {branch.get('phone', '+91-9594790929')}",
                f"Email: {branch.get('email', 'Sujalfashionworks@gmail.com')}",
            ])
            # V23: lower block was too small in real PRN print. Make it same bold/readable
            # style as product text. Keep only the most important 5 lines to avoid overlap.
            lower_y = [197, 181, 165, 149, 133]
            for yy, txt in zip(lower_y, lower_lines[:len(lower_y)]):
                lines.append(self._prn_text(text_x, yy, 'ROMAN.TTF', 180, 1, 5, self._tspl_clean(txt, 52)))

        # Working BarTender barcode values: do not change while scanning works.
        lines.append(self._prn_barcode(barcode_x, barcode_y, barcode, fmt))
        lines.append(self._prn_text(code_x, code_y, 'ROMAN.TTF', 180, 1, 8, barcode))
        return lines

    def _reference_prn_path(self):
        return BASE_DIR / "reference_templates" / "working_bartender_reference_hhhh.prn"

    def _reference_prn_preamble(self):
        """Return the BarTender static preamble/BITMAP section before CODEPAGE.
        This preserves the exact printer setup/background from the working PRN.
        If the reference file is not available, return an empty string and fall back
        to command-generated header.
        """
        try:
            p = self._reference_prn_path()
            if not p.exists():
                return ""
            raw = p.read_bytes()
            marker = b"CODEPAGE 1252"
            idx = raw.find(marker)
            if idx <= 0:
                return ""
            pre = raw[:idx]
            return pre.decode("latin1", errors="ignore").rstrip("\r\n")
        except Exception as e:
            log("reference prn preamble failed: " + str(e))
            return ""

    def _prn_header(self):
        return [
            'SIZE 101.5 mm, 50 mm',
            'GAP 3 mm, 0 mm',
            'SPEED 3',
            'DENSITY 10',
            'SET RIBBON OFF',
            'DIRECTION 0,0',
            'REFERENCE 0,0',
            'OFFSET 0 mm',
            'SET PEEL OFF',
            'SET CUTTER OFF',
            'SET PARTIAL_CUTTER OFF',
            'SET TEAR ON',
        ]

    def _iter_print_rows(self, files_snapshot):
        for item in files_snapshot:
            df = item['df']
            for ridx, row in df.iterrows():
                qty = safe_int(item.get('qty', {}).get(int(ridx), 1), 1)
                for _ in range(qty):
                    yield item['format'], df, row

    def generate_prn_clicked(self, auto_print=False):
        self._auto_print_after_prn = bool(auto_print)
        if not self.files:
            messagebox.showwarning('No files', 'Upload files first.')
            return
        total = self.total_print_labels()
        if total > 50000:
            messagebox.showerror('Too many labels', 'Please generate below 50,000 labels at once.')
            return
        custom_name = simpledialog.askstring('PRN output name', 'Enter PRN output name (optional):', parent=self) or ''
        purpose = simpledialog.askstring('Purpose', 'Enter purpose:', initialvalue='Marketplace_PRN_Print_File', parent=self) or 'Marketplace_PRN_Print_File'
        branch = copy.deepcopy(self.current_branch())
        files_snapshot = [{'df': item['df'].copy(), 'format': item['format'], 'qty': dict(item.get('qty', {})), 'path': item.get('path','')} for item in self.files]
        if central_output_path:
            out = str(central_output_path('Marketplace_Product_PRN', 'MARKETPLACE_PRN', custom_name, purpose, 'batch', '.prn'))
        else:
            stamp = time.strftime('%Y%m%d_%H%M%S')
            prn_dir = Path.home() / 'Desktop' / 'MMS_Label_Tools_Output' / 'Marketplace_Product_PRN'
            prn_dir.mkdir(parents=True, exist_ok=True)
            out = str(prn_dir / f'marketplace_labels_{stamp}.prn')
        try:
            self.generate_prn_btn.config(state='disabled')
        except Exception:
            pass
        self.status_var.set(f'Generating PRN... {total} labels')
        self.update_idletasks()

        def worker():
            try:
                self.generate_prn_worker(out, branch, files_snapshot, total)
                self.after(0, lambda: self.on_prn_done(out, total, purpose, custom_name))
            except Exception as e:
                err = str(e)
                log(traceback.format_exc())
                self.after(0, lambda: self.on_prn_error(err))
        threading.Thread(target=worker, daemon=True).start()

    def generate_prn_worker(self, out, branch, files_snapshot, total):
        rows = list(self._iter_print_rows(files_snapshot))
        out_lines = []
        ref_preamble = self._reference_prn_preamble()
        for i in range(0, len(rows), 2):
            if ref_preamble:
                # Use the real BarTender PRN preamble/bitmap exactly, then replace only variable data.
                out_lines.append(ref_preamble)
            else:
                out_lines.extend(self._prn_header())
                out_lines.append('CLS')
            out_lines.append('CODEPAGE 1252')
            # Real BarTender PRN writes right label first, then left label.
            fmt, df, row = rows[i]
            out_lines.extend(self._make_prn_label_lines('right', fmt, df, row, branch))
            if i + 1 < len(rows):
                fmt2, df2, row2 = rows[i + 1]
                out_lines.extend(self._make_prn_label_lines('left', fmt2, df2, row2, branch))
            out_lines.append('PRINT 1,1')
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        # latin1 preserves binary/bitmap bytes copied from the BarTender PRN preamble.
        Path(out).write_text('\r\n'.join(out_lines) + '\r\n', encoding='latin1', errors='ignore')

    def on_prn_done(self, out, total, purpose='', custom_name=''):

        self.last_prn = out
        try:
            self.generate_prn_btn.config(state='normal')
        except Exception:
            pass
        try:
            record_output('Marketplace Product Label Generator V12 - PRN', out, purpose, custom_name, [i.get('path', '') for i in self.files], f'{total} PRN labels, TSPL Code39 native printer commands')
        except Exception:
            pass
        self.status_var.set(f'PRN generated: {total} labels → {out}')
        if getattr(self, '_auto_print_after_prn', False):
            self._auto_print_after_prn = False
            self.print_prn_file(out)
        else:
            messagebox.showinfo('PRN generated', f'PRN generated successfully.\n\nLabels: {total}\nType: TSPL/TSC native print file based on your BarTender PRN.\n\nUse this PRN for actual thermal barcode printing.\n\nFile:\n{out}')

    def on_prn_error(self, err):
        try:
            self.generate_prn_btn.config(state='normal')
        except Exception:
            pass
        messagebox.showerror('PRN error', err)
        self.status_var.set('PRN generation failed. Check logs/debug_log.txt')

    # ---------------- Direct RAW PRN printing ----------------
    def printer_settings_path(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            return DATA_DIR / "printer_settings.json"
        except Exception:
            return Path.home() / "Desktop" / "mms_printer_settings.json"

    def load_selected_printer(self):
        try:
            p = self.printer_settings_path()
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                return data.get("selected_printer", "")
        except Exception:
            pass
        return ""

    def save_selected_printer(self, name):
        self.selected_printer = name or ""
        try:
            p = self.printer_settings_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"selected_printer": self.selected_printer}, indent=2), encoding="utf-8")
        except Exception as e:
            log("save printer settings failed: " + str(e))

    def list_windows_printers(self):
        names = []
        try:
            import win32print
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            for item in win32print.EnumPrinters(flags):
                # tuple: flags, description, name, comment
                if len(item) >= 3 and item[2]:
                    names.append(item[2])
        except Exception:
            pass
        if not names:
            try:
                # fallback without pywin32
                import subprocess
                ps = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Printer | Select-Object -ExpandProperty Name"], capture_output=True, text=True, timeout=8)
                if ps.returncode == 0:
                    names = [x.strip() for x in ps.stdout.splitlines() if x.strip()]
            except Exception:
                pass
        # unique stable order
        out = []
        seen = set()
        for n in names:
            if n not in seen:
                out.append(n)
                seen.add(n)
        return out

    def select_printer_dialog(self):
        printers = self.list_windows_printers()
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("Select Thermal Printer")
        dlg.geometry("560x430")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()
        ttk.Label(dlg, text="Select your thermal printer for direct PRN printing", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(14, 4))
        ttk.Label(dlg, text="This sends TSPL/PRN commands directly to the selected printer. Use the same printer that works with BarTender.").pack(anchor="w", padx=14, pady=(0, 10))
        frame = ttk.Frame(dlg)
        frame.pack(fill="both", expand=True, padx=14, pady=8)
        lb = tk.Listbox(frame, height=12)
        lb.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, command=lb.yview)
        sb.pack(side="right", fill="y")
        lb.configure(yscrollcommand=sb.set)
        for p in printers:
            lb.insert("end", p)
            if p == self.selected_printer:
                lb.selection_set("end")
        manual_var = tk.StringVar(value=self.selected_printer)
        row = ttk.Frame(dlg)
        row.pack(fill="x", padx=14, pady=8)
        ttk.Label(row, text="Manual printer name:").pack(side="left")
        ttk.Entry(row, textvariable=manual_var).pack(side="left", fill="x", expand=True, padx=8)

        def use_selected():
            sel = lb.curselection()
            if sel:
                manual_var.set(lb.get(sel[0]))

        def save_and_close():
            use_selected()
            name = manual_var.get().strip()
            if not name:
                messagebox.showwarning("Printer required", "Select or type a printer name.", parent=dlg)
                return
            self.save_selected_printer(name)
            self.status_var.set(f"Selected printer: {name}")
            dlg.destroy()

        btns = ttk.Frame(dlg)
        btns.pack(fill="x", padx=14, pady=(4, 14))
        ttk.Button(btns, text="Use Selected", command=use_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="Save Printer", command=save_and_close).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=dlg.destroy).pack(side="right", padx=4)

    def print_prn_file(self, prn_path):
        if not prn_path or not os.path.exists(prn_path):
            messagebox.showwarning("No PRN", "Generate PRN first.")
            return False
        printer = (self.selected_printer or "").strip()
        if not printer:
            messagebox.showwarning("Select printer", "Select your thermal printer first using Select Printer.")
            self.select_printer_dialog()
            printer = (self.selected_printer or "").strip()
            if not printer:
                return False
        try:
            import win32print
            raw = Path(prn_path).read_bytes()
            h = win32print.OpenPrinter(printer)
            try:
                job = win32print.StartDocPrinter(h, 1, ("MMS Tool2 PRN Labels", None, "RAW"))
                try:
                    win32print.StartPagePrinter(h)
                    win32print.WritePrinter(h, raw)
                    win32print.EndPagePrinter(h)
                finally:
                    win32print.EndDocPrinter(h)
            finally:
                win32print.ClosePrinter(h)
            self.status_var.set(f"PRN sent directly to printer: {printer}")
            messagebox.showinfo("Print sent", f"PRN sent directly to printer:\n{printer}\n\nFile:\n{prn_path}")
            return True
        except Exception as e:
            messagebox.showerror("Direct PRN print failed", "Direct RAW printing needs pywin32 and the correct Windows printer driver.\n\nTry INSTALL_REQUIREMENTS.bat again, select the printer, and retry.\n\nError:\n" + str(e))
            log(traceback.format_exc())
            return False

    def print_last_prn(self):
        if not self.last_prn or not os.path.exists(self.last_prn):
            messagebox.showwarning("No PRN", "Generate PRN first.")
            return
        self.print_prn_file(self.last_prn)

    def open_last_prn_folder(self):
        if not self.last_prn or not os.path.exists(self.last_prn):
            messagebox.showwarning('No PRN', 'Generate PRN first.')
            return
        try:
            os.startfile(str(Path(self.last_prn).parent))
        except Exception as e:
            messagebox.showerror('Open folder error', str(e))

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
        custom_name = simpledialog.askstring("Output name", "Enter output name (optional):", parent=self) or ""
        purpose = simpledialog.askstring("Purpose", "Enter purpose (example: Flipkart_Product_Labels):", initialvalue="Marketplace_Product_Labels", parent=self) or "Marketplace_Product_Labels"
        self._last_output_custom_name = custom_name
        self._last_output_purpose = purpose
        if central_output_path:
            out = str(central_output_path("Marketplace_Product_Labels", "MARKETPLACE_LABELS", custom_name, purpose, "batch", ".pdf"))
        else:
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
        try:
            record_output("Marketplace Product Label Generator V12", out, getattr(self, "_last_output_purpose", "Marketplace_Product_Labels"), getattr(self, "_last_output_custom_name", ""), [i.get("path", "") for i in self.files], f"{total} labels")
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

    def print_last_pdf(self):
        if not self.last_pdf or not os.path.exists(self.last_pdf):
            messagebox.showwarning("No PDF", "Generate PDF first.")
            return
        try:
            os.startfile(self.last_pdf, "print")
            self.status_var.set("Print command sent. Use Actual Size / 100% / No Scaling.")
        except Exception as e:
            messagebox.showerror("Print error", f"Open PDF and press Ctrl+P.\n\n{e}")


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
    dummy = object()
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
    print(f"SELF TEST OK: generated {count} labels at {out}")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    try:
        app = App()
        app.root_window.mainloop()
    except Exception:
        log(traceback.format_exc())
        raise
