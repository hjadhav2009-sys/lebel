import copy
import json
import os
import platform
import subprocess
import threading
import time
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from amazon_label_renderer import (
    amazon_display_heading,
    amazon_mrp_for_print,
    amazon_title_for_print,
    generate_amazon_pdf,
    wrap_text,
)
from amazon_prn_renderer import generate_amazon_prn
from amazon_reader import load_consignment_file, load_master_listing_file
from amazon_rules import (
    clean_text,
    load_brand_rules,
    load_category_rules,
    load_mapping_settings,
    merge_sheet_options,
    save_brand_manual_rule,
    save_category_manual_rule,
    save_mapping_settings,
)
from amazon_validation import (
    has_blocking_errors,
    parse_positive_int,
    resolve_amazon_rows,
    validate_amazon_rows,
)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "outputs"
LOG_DIR = BASE_DIR / "logs"
BRANCHES_FILE = DATA_DIR / "branches.json"
LOG_FILE = LOG_DIR / "debug_log.txt"


def log(msg):
    try:
        LOG_DIR.mkdir(exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " | AMAZON | " + str(msg) + "\n")
    except Exception:
        pass


def load_old_branches():
    try:
        if BRANCHES_FILE.exists():
            data = json.loads(BRANCHES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        log(traceback.format_exc())
    return {}


def open_file(path):
    if not path or not Path(path).exists():
        raise RuntimeError("File not found.")
    if os.name == "nt":
        os.startfile(str(path))
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def print_raw_file(path):
    path = Path(path)
    if not path.exists():
        raise RuntimeError("PRN file not found.")
    if os.name != "nt":
        subprocess.run(["lpr", str(path)], check=True)
        return "default printer"

    import ctypes
    from ctypes import wintypes

    winspool = ctypes.WinDLL("winspool.drv")

    class DOC_INFO_1(ctypes.Structure):
        _fields_ = [
            ("pDocName", wintypes.LPWSTR),
            ("pOutputFile", wintypes.LPWSTR),
            ("pDatatype", wintypes.LPWSTR),
        ]

    winspool.GetDefaultPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    winspool.GetDefaultPrinterW.restype = wintypes.BOOL
    winspool.OpenPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.HANDLE), wintypes.LPVOID]
    winspool.OpenPrinterW.restype = wintypes.BOOL
    winspool.StartDocPrinterW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(DOC_INFO_1)]
    winspool.StartDocPrinterW.restype = wintypes.DWORD
    winspool.StartPagePrinter.argtypes = [wintypes.HANDLE]
    winspool.StartPagePrinter.restype = wintypes.BOOL
    winspool.WritePrinter.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    winspool.WritePrinter.restype = wintypes.BOOL
    winspool.EndPagePrinter.argtypes = [wintypes.HANDLE]
    winspool.EndPagePrinter.restype = wintypes.BOOL
    winspool.EndDocPrinter.argtypes = [wintypes.HANDLE]
    winspool.EndDocPrinter.restype = wintypes.BOOL
    winspool.ClosePrinter.argtypes = [wintypes.HANDLE]
    winspool.ClosePrinter.restype = wintypes.BOOL

    needed = wintypes.DWORD(0)
    winspool.GetDefaultPrinterW(None, ctypes.byref(needed))
    if needed.value == 0:
        raise RuntimeError("No default printer is configured in Windows.")
    printer_buffer = ctypes.create_unicode_buffer(needed.value)
    if not winspool.GetDefaultPrinterW(printer_buffer, ctypes.byref(needed)):
        raise ctypes.WinError()

    printer_name = printer_buffer.value
    handle = wintypes.HANDLE()
    if not winspool.OpenPrinterW(printer_name, ctypes.byref(handle), None):
        raise ctypes.WinError()

    doc_started = False
    page_started = False
    try:
        doc_info = DOC_INFO_1("Amazon Labels Tool 2 PRN", None, "RAW")
        if winspool.StartDocPrinterW(handle, 1, ctypes.byref(doc_info)) == 0:
            raise ctypes.WinError()
        doc_started = True
        if not winspool.StartPagePrinter(handle):
            raise ctypes.WinError()
        page_started = True
        raw = path.read_bytes()
        raw_buffer = ctypes.create_string_buffer(raw)
        written = wintypes.DWORD(0)
        if not winspool.WritePrinter(handle, raw_buffer, len(raw), ctypes.byref(written)):
            raise ctypes.WinError()
        if written.value != len(raw):
            raise RuntimeError(f"Only {written.value} of {len(raw)} bytes were sent to printer.")
    finally:
        if page_started:
            winspool.EndPagePrinter(handle)
        if doc_started:
            winspool.EndDocPrinter(handle)
        winspool.ClosePrinter(handle)

    return printer_name


class AmazonLabelWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Amazon Labels - Tool 2")
        self.geometry("1340x840")
        self.minsize(1120, 720)

        OUT_DIR.mkdir(exist_ok=True)
        self.branches = load_old_branches()
        self.mapping = load_mapping_settings()
        self.category_rules = load_category_rules()
        self.brand_rules = load_brand_rules()

        self.master_data = None
        self.consignment_data = None
        self.rows = []
        self.row_overrides = {}
        self.manual_mrp = {}
        self.qty_overrides = {}
        self.last_pdf = ""
        self.last_prn = ""
        self._busy_count = 0

        self.branch_var = tk.StringVar()
        self.master_path_var = tk.StringVar(value="Weekly master listing: not loaded")
        self.consignment_path_var = tk.StringVar(value="Amazon consignment: not loaded")
        self.status_var = tk.StringVar(value="Ready")

        self.build_ui()
        self.refresh_branches()
        self.draw_empty_preview()

    def build_ui(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=10, pady=10)

        file_row = ttk.Frame(root)
        file_row.pack(fill="x", pady=(0, 6))
        ttk.Label(file_row, text="Files:").pack(side="left", padx=(0, 8))
        self.upload_master_btn = ttk.Button(file_row, text="Upload Weekly Master Listing", command=self.upload_master_listing)
        self.upload_master_btn.pack(side="left", padx=3)
        self.upload_consignment_btn = ttk.Button(file_row, text="Upload Amazon Consignment File", command=self.upload_consignment_file)
        self.upload_consignment_btn.pack(side="left", padx=3)
        ttk.Button(file_row, text="Clear Amazon Consignment", command=self.clear_consignment).pack(side="left", padx=3)
        ttk.Button(file_row, text="Clear Master Listing", command=self.clear_master_listing).pack(side="left", padx=3)

        check_row = ttk.Frame(root)
        check_row.pack(fill="x", pady=(0, 6))
        ttk.Label(check_row, text="Check:").pack(side="left", padx=(0, 8))
        ttk.Button(check_row, text="Preview Selected", command=self.preview_selected).pack(side="left", padx=3)
        ttk.Button(check_row, text="Validate Amazon", command=lambda: self.validate_amazon(show_message=True)).pack(side="left", padx=3)
        ttk.Button(check_row, text="Fix Blocking Rows", command=self.fix_blocking_rows).pack(side="left", padx=3)

        output_row = ttk.Frame(root)
        output_row.pack(fill="x", pady=(0, 6))
        ttk.Label(output_row, text="Output:").pack(side="left", padx=(0, 8))
        self.generate_pdf_btn = ttk.Button(output_row, text="Generate Amazon PDF", command=self.generate_pdf_clicked)
        self.generate_pdf_btn.pack(side="left", padx=3)
        self.generate_prn_btn = ttk.Button(output_row, text="Generate Amazon PRN", command=self.generate_prn_clicked)
        self.generate_prn_btn.pack(side="left", padx=3)
        ttk.Button(output_row, text="Open Last PDF", command=self.open_last_pdf).pack(side="left", padx=3)
        ttk.Button(output_row, text="Open Last PRN", command=self.open_last_prn).pack(side="left", padx=3)
        ttk.Button(output_row, text="Print Last PRN Direct", command=self.print_last_prn_direct).pack(side="left", padx=3)

        branch_row = ttk.Frame(root)
        branch_row.pack(fill="x", pady=(0, 6))
        ttk.Label(branch_row, text="Branch:").pack(side="left", padx=(0, 8))
        self.branch_combo = ttk.Combobox(branch_row, textvariable=self.branch_var, state="readonly", width=34)
        self.branch_combo.pack(side="left")
        self.branch_combo.bind("<<ComboboxSelected>>", self.on_branch_changed)
        ttk.Label(branch_row, textvariable=self.master_path_var).pack(side="left", padx=(22, 8))
        ttk.Label(branch_row, textvariable=self.consignment_path_var).pack(side="left", padx=8)

        body = ttk.Panedwindow(root, orient="horizontal")
        body.pack(fill="both", expand=True, pady=(4, 6))
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)

        ttk.Label(left, text="Amazon Validation").pack(anchor="w")
        table_frame = ttk.Frame(left)
        table_frame.pack(fill="both", expand=True, pady=(3, 0))
        columns = ("status", "sku", "asin", "fnsku", "heading", "brand", "mrp", "qty", "errors")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=22)
        headings = {
            "status": ("Status", 70),
            "sku": ("SKU", 130),
            "asin": ("ASIN/Product ID", 115),
            "fnsku": ("FNSKU", 125),
            "heading": ("Main Heading", 130),
            "brand": ("Brand", 120),
            "mrp": ("MRP", 80),
            "qty": ("Qty", 55),
            "errors": ("Error message", 320),
        }
        for col in columns:
            label, width = headings[col]
            self.table.heading(col, text=label)
            self.table.column(col, width=width, minwidth=45, anchor="w", stretch=(col == "errors"))
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.table.tag_configure("fail", background="#ffecec")
        self.table.tag_configure("pass", background="#ecfff0")
        self.table.bind("<<TreeviewSelect>>", lambda _event: self.preview_selected())

        ttk.Label(right, text="Preview").pack(anchor="w")
        self.preview = tk.Canvas(right, bg="#f4f4f4", highlightthickness=1, highlightbackground="#cccccc")
        self.preview.pack(fill="both", expand=True, pady=(3, 0))
        self.preview.bind("<Configure>", lambda _event: self.preview_selected(silent=True))

        status_row = ttk.Frame(root)
        status_row.pack(fill="x")
        ttk.Label(status_row, textvariable=self.status_var).pack(side="left")
        ttk.Label(status_row, text="Amazon Tool 2: PDF/PRN 101.5mm x 50mm, 2-up, label 49.8mm x 49.8mm.").pack(side="right")

    def set_busy(self, busy):
        self._busy_count += 1 if busy else -1
        self._busy_count = max(0, self._busy_count)
        state = "disabled" if self._busy_count else "normal"
        for button in (self.upload_master_btn, self.upload_consignment_btn, self.generate_pdf_btn, self.generate_prn_btn):
            try:
                button.config(state=state)
            except Exception:
                pass

    def run_background(self, status, work, done):
        self.status_var.set(status)
        self.set_busy(True)

        def worker():
            try:
                result = work()
            except Exception as exc:
                err = str(exc)
                log(traceback.format_exc())
                self.after(0, lambda: self.on_background_error(err))
            else:
                self.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()

    def on_background_error(self, err):
        self.set_busy(False)
        self.status_var.set("Amazon task failed. Check logs/debug_log.txt.")
        messagebox.showerror("Amazon Labels", err)

    def refresh_branches(self):
        self.branches = load_old_branches()
        names = list(self.branches.keys())
        self.branch_combo["values"] = names
        selected = self.mapping.get("selected_branch", "")
        if selected not in self.branches and names:
            selected = names[0]
        self.branch_var.set(selected)

    def current_branch(self):
        name = self.branch_var.get()
        if name in self.branches:
            return self.branches[name]
        return next(iter(self.branches.values()), {})

    def on_branch_changed(self, _event=None):
        self.mapping["selected_branch"] = self.branch_var.get()
        save_mapping_settings(self.mapping)
        if self.consignment_data:
            self.validate_amazon(show_message=False)

    def upload_master_listing(self):
        path = filedialog.askopenfilename(
            title="Select Weekly Master Listing",
            filetypes=[("Excel Workbooks", "*.xlsx *.xls"), ("All Files", "*.*")],
        )
        if not path:
            return

        def work():
            return load_master_listing_file(path, copy.deepcopy(self.mapping))

        self.run_background("Loading weekly master listing in background...", work, self.on_master_loaded)

    def on_master_loaded(self, data):
        self.set_busy(False)
        self.master_data = data
        self.mapping["last_master_path"] = data.get("path", "")
        save_mapping_settings(self.mapping)
        self.master_path_var.set(f"Weekly master listing: {Path(data.get('path', '')).name}")
        rows = 0
        try:
            rows = len(data.get("master_df"))
        except Exception:
            rows = 0
        self.status_var.set(f"Loaded weekly master listing: {rows} rows.")
        if self.consignment_data:
            self.validate_amazon(show_message=False)

    def upload_consignment_file(self):
        path = filedialog.askopenfilename(
            title="Select Amazon Consignment File",
            filetypes=[("Excel Workbooks", "*.xlsx *.xls"), ("All Files", "*.*")],
        )
        if not path:
            return

        def work():
            return load_consignment_file(path, copy.deepcopy(self.mapping))

        self.run_background("Loading Amazon consignment file in background...", work, self.on_consignment_loaded)

    def on_consignment_loaded(self, data):
        self.set_busy(False)
        self.consignment_data = data
        merge_sheet_options(data.get("sheet_categories", []), data.get("sheet_brands", []))
        self.category_rules = load_category_rules()
        self.brand_rules = load_brand_rules()
        self.consignment_path_var.set(f"Amazon consignment: {Path(data.get('path', '')).name}")
        self.validate_amazon(show_message=False)

    def clear_consignment(self):
        self.consignment_data = None
        self.rows = []
        self.row_overrides.clear()
        self.manual_mrp.clear()
        self.qty_overrides.clear()
        self.consignment_path_var.set("Amazon consignment: not loaded")
        self.refresh_table()
        self.draw_empty_preview()
        self.status_var.set("Amazon consignment cleared.")

    def clear_master_listing(self):
        self.master_data = None
        self.mapping["last_master_path"] = ""
        save_mapping_settings(self.mapping)
        self.master_path_var.set("Weekly master listing: not loaded")
        if self.consignment_data:
            self.validate_amazon(show_message=False)
        else:
            self.status_var.set("Weekly master listing cleared.")

    def master_df(self):
        if self.master_data:
            return self.master_data.get("master_df")
        return None

    def apply_manual_overrides(self, rows):
        for row in rows:
            key = row.get("row_key", "")
            overrides = self.row_overrides.get(key, {})
            for field in ("merchant_sku", "title", "asin", "fnsku", "main_heading", "brand", "generic_name", "mrp"):
                value = clean_text(overrides.get(field, ""))
                if value:
                    row[field] = value
            qty = clean_text(overrides.get("print_qty", ""))
            if qty:
                row["print_qty"] = parse_positive_int(qty)
        return rows

    def resolve_rows(self):
        if not self.consignment_data:
            return []
        self.category_rules = load_category_rules()
        self.brand_rules = load_brand_rules()
        rows = resolve_amazon_rows(
            self.consignment_data,
            copy.deepcopy(self.mapping),
            self.category_rules,
            self.brand_rules,
            manual_mrp=self.manual_mrp,
            qty_overrides=self.qty_overrides,
            master_df=self.master_df(),
        )
        return self.apply_manual_overrides(rows)

    def validate_amazon(self, show_message=False):
        if not self.consignment_data:
            messagebox.showwarning("No consignment", "Upload Amazon consignment file first.")
            return []
        rows = self.resolve_rows()
        rows = validate_amazon_rows(rows, self.current_branch())
        self.rows = rows
        self.refresh_table()
        self.preview_selected(silent=True)
        failures = sum(1 for row in rows if row.get("errors"))
        if failures:
            self.status_var.set(f"Amazon validation blocked: {failures} row(s) need fixes.")
            if show_message:
                messagebox.showwarning("Amazon validation", f"{failures} row(s) have blocking errors. Use Fix Blocking Rows.")
        else:
            total = sum(parse_positive_int(row.get("print_qty", 0)) for row in rows)
            self.status_var.set(f"Amazon validation passed: {len(rows)} rows, {total} labels.")
            if show_message:
                messagebox.showinfo("Amazon validation", f"Validation passed.\n\nRows: {len(rows)}\nLabels: {total}")
        return rows

    def refresh_table(self):
        for item in self.table.get_children():
            self.table.delete(item)
        for index, row in enumerate(self.rows):
            tag = "fail" if row.get("errors") else "pass"
            self.table.insert(
                "",
                "end",
                iid=str(index),
                tags=(tag,),
                values=(
                    row.get("status", ""),
                    row.get("merchant_sku", ""),
                    row.get("asin", ""),
                    row.get("fnsku", ""),
                    row.get("main_heading", ""),
                    row.get("brand", ""),
                    row.get("mrp", ""),
                    row.get("print_qty", ""),
                    "; ".join(row.get("errors", [])),
                ),
            )

    def selected_index(self):
        selection = self.table.selection()
        if not selection:
            return None
        try:
            idx = int(selection[0])
        except Exception:
            return None
        return idx if 0 <= idx < len(self.rows) else None

    def preview_selected(self, silent=False):
        if not self.rows:
            if not silent:
                self.validate_amazon(show_message=False)
            if not self.rows:
                self.draw_empty_preview()
                return
        idx = self.selected_index()
        if idx is None:
            idx = 0
            try:
                self.table.selection_set(str(idx))
            except Exception:
                pass
        self.draw_preview_page(idx)

    def draw_empty_preview(self):
        self.preview.delete("all")
        width = max(400, self.preview.winfo_width())
        height = max(300, self.preview.winfo_height())
        self.preview.create_text(width / 2, height / 2, text="Upload and validate Amazon files", fill="#777777", font=("Arial", 14))

    def draw_preview_page(self, row_index):
        self.preview.delete("all")
        canvas_w = max(500, self.preview.winfo_width())
        canvas_h = max(330, self.preview.winfo_height())
        page_w = 101.5
        page_h = 50.0
        scale = min((canvas_w - 40) / page_w, (canvas_h - 40) / page_h)
        w = page_w * scale
        h = page_h * scale
        x0 = (canvas_w - w) / 2
        y0 = (canvas_h - h) / 2
        self.preview.create_rectangle(x0, y0, x0 + w, y0 + h, fill="#ffffff", outline="#999999")

        label_w = 49.8 * scale
        label_h = 49.8 * scale
        gap = (page_w - 49.8 * 2) * scale
        label_y = y0 + (h - label_h) / 2
        for side in range(2):
            idx = row_index + side
            label_x = x0 + side * (label_w + gap)
            if idx < len(self.rows):
                self.draw_preview_label(label_x, label_y, label_w, label_h, self.rows[idx])
            else:
                self.preview.create_rectangle(label_x, label_y, label_x + label_w, label_y + label_h, outline="#cccccc")

    def draw_preview_label(self, x, y, w, h, row):
        branch = self.current_branch()
        self.preview.create_rectangle(x, y, x + w, y + h, fill="#ffffff", outline="#111111")

        def sx(mm_value):
            return x + (mm_value / 49.8) * w

        def sy(mm_value):
            return y + (mm_value / 49.8) * h

        heading = amazon_display_heading(row.get("main_heading", ""))[:26]
        self.preview.create_text(x + w / 2, sy(4.6), text=heading, font=("Arial", 10, "bold"), anchor="n")

        details = [
            ("Brand", row.get("brand", "")),
            ("SKU No", row.get("merchant_sku", "")),
            ("Net Quantity", "1 N"),
            ("MRP", amazon_mrp_for_print(row.get("mrp", ""))),
            ("Generic Name", amazon_display_heading(row.get("generic_name", ""))),
        ]
        yy = sy(11.0)
        for label, value in details:
            text = f"{label}: {clean_text(value)}"
            self.preview.create_text(sx(2.2), yy, text=text[:58], font=("Arial", 6), anchor="w")
            yy += 13

        self.preview.create_line(sx(1.8), sy(27.0), sx(48.0), sy(27.0), fill="#777777")
        self.preview.create_text(
            sx(2.2),
            sy(28.2),
            text="Manufactured by / Marketed By / Customer care Details:",
            font=("Arial", 5, "bold"),
            anchor="w",
        )

        address_lines = []
        for value in (branch.get("marketed_by", ""), branch.get("address", "")):
            address_lines.extend(wrap_text(value, 42))
        address_lines.extend(
            [
                f"Email Id:{clean_text(branch.get('email', ''))}",
                f"Contact:{clean_text(branch.get('phone', ''))}",
                f"Origin:{clean_text(branch.get('origin', 'Country of Origin: India')).split(':')[-1].strip() or 'India'}",
            ]
        )
        yy = sy(31.0)
        for line in address_lines[:5]:
            self.preview.create_text(sx(2.2), yy, text=line[:54], font=("Arial", 5), anchor="w")
            yy += 9

        barcode_top = sy(39.0)
        barcode_bottom = sy(45.6)
        self.preview.create_rectangle(sx(7.0), barcode_top, sx(42.8), barcode_bottom, fill="#eeeeee", outline="#222222")
        fnsku = clean_text(row.get("fnsku", ""))
        self.preview.create_text(x + w / 2, sy(46.6), text=fnsku, font=("Arial", 6), anchor="n")
        self.preview.create_text(x + w / 2, sy(48.3), text=amazon_title_for_print(row.get("title", ""))[:58], font=("Arial", 5), anchor="n")

    def fix_blocking_rows(self):
        rows = self.validate_amazon(show_message=False)
        failing = [idx for idx, row in enumerate(rows) if row.get("errors")]
        if not failing:
            messagebox.showinfo("Fix Blocking Rows", "No blocking rows to fix.")
            return
        selected = self.selected_index()
        start = selected if selected in failing else failing[0]

        win = tk.Toplevel(self)
        win.title("Fix Amazon Blocking Rows")
        win.geometry("560x420")
        win.transient(self)
        win.grab_set()

        current = {"index": start}
        error_var = tk.StringVar()
        row_title_var = tk.StringVar()
        sku_var = tk.StringVar()
        fnsku_var = tk.StringVar()
        heading_var = tk.StringVar()
        brand_var = tk.StringVar()
        mrp_var = tk.StringVar()
        qty_var = tk.StringVar()

        top = ttk.Frame(win)
        top.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(top, textvariable=row_title_var, font=("Arial", 10, "bold")).pack(anchor="w")
        ttk.Label(top, textvariable=error_var, foreground="#9a0000", wraplength=520).pack(anchor="w", pady=(3, 0))

        form = ttk.Frame(win)
        form.pack(fill="x", padx=10, pady=8)
        fields = [
            ("SKU", sku_var, None),
            ("FNSKU", fnsku_var, None),
            ("Main Heading", heading_var, self.category_rules.get("categories", [])),
            ("Brand", brand_var, self.brand_rules.get("brands", [])),
            ("MRP", mrp_var, None),
            ("Quantity", qty_var, None),
        ]
        for row_no, (label, variable, values) in enumerate(fields):
            ttk.Label(form, text=label, width=16).grid(row=row_no, column=0, sticky="w", pady=4)
            if values is None:
                widget = ttk.Entry(form, textvariable=variable, width=48)
            else:
                widget = ttk.Combobox(form, textvariable=variable, width=46, values=values)
            widget.grid(row=row_no, column=1, sticky="ew", pady=4)
        form.columnconfigure(1, weight=1)

        def load_row():
            idx = current["index"]
            row = self.rows[idx]
            row_title_var.set(f"Row {idx + 1} of {len(self.rows)}")
            error_var.set("; ".join(row.get("errors", [])))
            sku_var.set(row.get("merchant_sku", ""))
            fnsku_var.set(row.get("fnsku", ""))
            heading_var.set(row.get("main_heading", ""))
            brand_var.set(row.get("brand", ""))
            mrp_var.set(row.get("mrp", ""))
            qty_var.set(str(row.get("print_qty", "")))

        def save_current():
            idx = current["index"]
            row = self.rows[idx]
            key = row.get("row_key", "")
            overrides = self.row_overrides.setdefault(key, {})
            values = {
                "merchant_sku": sku_var.get(),
                "fnsku": fnsku_var.get(),
                "main_heading": heading_var.get(),
                "brand": brand_var.get(),
                "mrp": mrp_var.get(),
                "print_qty": qty_var.get(),
            }
            for field, value in values.items():
                value = clean_text(value)
                if value:
                    overrides[field] = value
            if clean_text(heading_var.get()):
                save_category_manual_rule(row, heading_var.get())
            if clean_text(brand_var.get()):
                save_brand_manual_rule(row, brand_var.get())
            if clean_text(mrp_var.get()):
                self.manual_mrp[key] = mrp_var.get()
                asin = clean_text(row.get("asin", "")).lower()
                if asin:
                    self.manual_mrp[asin] = mrp_var.get()
            if clean_text(qty_var.get()):
                self.qty_overrides[key] = qty_var.get()
            self.category_rules = load_category_rules()
            self.brand_rules = load_brand_rules()
            self.validate_amazon(show_message=False)

        def save_and_next():
            save_current()
            failing_now = [idx for idx, row in enumerate(self.rows) if row.get("errors")]
            if not failing_now:
                messagebox.showinfo("Fix Blocking Rows", "All blocking rows are fixed.")
                win.destroy()
                return
            after_current = [idx for idx in failing_now if idx > current["index"]]
            current["index"] = after_current[0] if after_current else failing_now[0]
            try:
                self.table.selection_set(str(current["index"]))
                self.table.see(str(current["index"]))
            except Exception:
                pass
            load_row()

        buttons = ttk.Frame(win)
        buttons.pack(fill="x", padx=10, pady=10)
        ttk.Button(buttons, text="Save", command=lambda: (save_current(), load_row())).pack(side="left", padx=4)
        ttk.Button(buttons, text="Save & Next Blocking", command=save_and_next).pack(side="left", padx=4)
        ttk.Button(buttons, text="Close", command=win.destroy).pack(side="right", padx=4)

        try:
            self.table.selection_set(str(start))
            self.table.see(str(start))
        except Exception:
            pass
        load_row()

    def prepare_valid_rows(self):
        rows = self.validate_amazon(show_message=False)
        if not rows:
            messagebox.showwarning("No rows", "Upload and validate Amazon consignment first.")
            return None
        if has_blocking_errors(rows):
            messagebox.showerror("Blocking rows", "Fix blocking rows before generating Amazon PDF/PRN.")
            return None
        total = sum(parse_positive_int(row.get("print_qty", 0)) for row in rows)
        if total <= 0:
            messagebox.showerror("No labels", "No Amazon labels to generate. Check shipped quantity.")
            return None
        return copy.deepcopy(rows)

    def generate_pdf_clicked(self):
        rows = self.prepare_valid_rows()
        if rows is None:
            return
        branch = copy.deepcopy(self.current_branch())
        total = sum(parse_positive_int(row.get("print_qty", 0)) for row in rows)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = str(OUT_DIR / f"amazon_labels_tool2_{stamp}.pdf")

        def work():
            return generate_amazon_pdf(out, rows, branch, self.progress_callback("PDF"))

        self.run_background(f"Generating Amazon PDF in background... 0/{total}", work, lambda count: self.on_pdf_done(out, count))

    def generate_prn_clicked(self):
        rows = self.prepare_valid_rows()
        if rows is None:
            return
        branch = copy.deepcopy(self.current_branch())
        total = sum(parse_positive_int(row.get("print_qty", 0)) for row in rows)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = str(OUT_DIR / f"amazon_labels_tool2_{stamp}.prn")

        def work():
            return generate_amazon_prn(out, rows, branch, self.progress_callback("PRN"))

        self.run_background(f"Generating Amazon PRN in background... 0/{total}", work, lambda count: self.on_prn_done(out, count))

    def progress_callback(self, label):
        def update(done, total):
            self.after(0, lambda: self.status_var.set(f"Generating Amazon {label} in background... {done}/{total}"))

        return update

    def on_pdf_done(self, out, total):
        self.set_busy(False)
        self.last_pdf = out
        self.status_var.set(f"Amazon PDF generated: {total} labels -> {out}")
        messagebox.showinfo("Amazon PDF generated", f"Amazon PDF generated successfully.\n\nLabels: {total}\nFile:\n{out}")

    def on_prn_done(self, out, total):
        self.set_busy(False)
        self.last_prn = out
        self.status_var.set(f"Amazon PRN generated: {total} labels -> {out}")
        messagebox.showinfo("Amazon PRN generated", f"Amazon PRN generated successfully.\n\nLabels: {total}\nFile:\n{out}")

    def open_last_pdf(self):
        if not self.last_pdf:
            messagebox.showwarning("No PDF", "Generate Amazon PDF first.")
            return
        try:
            open_file(self.last_pdf)
        except Exception as exc:
            messagebox.showerror("Open PDF", str(exc))

    def open_last_prn(self):
        if not self.last_prn:
            messagebox.showwarning("No PRN", "Generate Amazon PRN first.")
            return
        try:
            open_file(self.last_prn)
        except Exception as exc:
            messagebox.showerror("Open PRN", str(exc))

    def print_last_prn_direct(self):
        if not self.last_prn:
            messagebox.showwarning("No PRN", "Generate Amazon PRN first.")
            return
        try:
            printer_name = print_raw_file(self.last_prn)
        except Exception as exc:
            log(traceback.format_exc())
            messagebox.showerror("Print PRN", str(exc))
            return
        self.status_var.set(f"Amazon PRN sent directly to {printer_name}.")
        messagebox.showinfo("Print PRN", f"Amazon PRN sent directly to:\n{printer_name}")
