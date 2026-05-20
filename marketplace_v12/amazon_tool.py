import copy
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

try:
    from . import amazon_label_renderer
    from . import amazon_prn_renderer
    from . import amazon_reader
    from . import amazon_rules
    from . import amazon_validation
except ImportError:
    import amazon_label_renderer
    import amazon_prn_renderer
    import amazon_reader
    import amazon_rules
    import amazon_validation

try:
    from output_manager import record_output, root_dir, subdir
except Exception:
    record_output = None
    root_dir = None
    subdir = None


BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "debug_log.txt"
LOCAL_OUT_DIR = BASE_DIR / "outputs"


def log_error(message):
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
            f.write(" AMAZON ")
            f.write(str(message).rstrip())
            f.write("\n")
    except Exception:
        pass


def output_dir():
    if subdir is not None:
        try:
            return subdir("Marketplace_Product_Labels")
        except Exception:
            pass
    LOCAL_OUT_DIR.mkdir(parents=True, exist_ok=True)
    return LOCAL_OUT_DIR


def printer_settings_path():
    if root_dir is not None:
        try:
            p = root_dir() / "Database" / "marketplace_v12" / "amazon_printer_settings.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass
    return BASE_DIR / "data" / "amazon_printer_settings.json"


class AmazonLabelFrame(ttk.Frame):
    TREE_COLS = ("status", "sku", "asin", "fnsku", "title", "heading", "brand", "mrp", "qty", "error")

    def __init__(self, master, branches_provider=None, current_branch_provider=None):
        super().__init__(master)
        self.branches_provider = branches_provider or (lambda: {})
        self.current_branch_provider = current_branch_provider or (lambda: None)

        self.mapping = amazon_rules.load_mapping_settings()
        self.category_rules = amazon_rules.load_category_rules()
        self.brand_rules = amazon_rules.load_brand_rules()

        self.master_data = None
        self.consignment_data = None
        self.master_df = None
        self.consignment_df = None
        self.master_path = ""
        self.consignment_path = ""
        self.amazon_rows = []
        self.manual_mrp = {}
        self.qty_overrides = {}
        self.tree_item_to_index = {}
        self.last_pdf = ""
        self.last_prn = ""
        self.last_report = ""

        self.status_var = tk.StringVar(value="Amazon Labels ready")
        self.master_status_var = tk.StringVar(value="Master Listing: not loaded")
        self.consignment_status_var = tk.StringVar(value="Consignment File: not loaded")
        self.branch_var = tk.StringVar(value=self.mapping.get("selected_branch", ""))
        self.layout_var = tk.StringVar(value=amazon_label_renderer.normalize_pdf_layout(self.mapping.get("pdf_layout", amazon_label_renderer.PDF_LAYOUT_BARTENDER)))
        self.qty_var = tk.StringVar(value="1")

        self.build_ui()
        self.refresh_branch_list()
        self.show_empty_preview()

    # ---------------- UI ----------------
    def build_ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=4, pady=(4, 2))

        files_row = ttk.Frame(toolbar)
        files_row.pack(fill="x", pady=2)
        ttk.Label(files_row, text="1) Files:").pack(side="left", padx=(0, 4))
        self.master_upload_btn = ttk.Button(files_row, text="Upload Weekly Master Listing", command=self.upload_master_file)
        self.master_upload_btn.pack(side="left", padx=3)
        self.consignment_upload_btn = ttk.Button(files_row, text="Upload Amazon Consignment File", command=self.upload_consignment_file)
        self.consignment_upload_btn.pack(side="left", padx=3)
        ttk.Button(files_row, text="Clear Amazon Consignment", command=self.clear_consignment).pack(side="left", padx=3)
        ttk.Button(files_row, text="Clear Master Listing", command=self.clear_master).pack(side="left", padx=3)

        check_row = ttk.Frame(toolbar)
        check_row.pack(fill="x", pady=2)
        ttk.Label(check_row, text="2) Check:").pack(side="left", padx=(0, 4))
        ttk.Button(check_row, text="Preview Selected", command=self.preview_selected).pack(side="left", padx=3)
        ttk.Button(check_row, text="Validate Amazon", command=self.validate_amazon_clicked).pack(side="left", padx=3)
        ttk.Button(check_row, text="Fix Blocking Rows", command=self.fix_blocking_rows_dialog).pack(side="left", padx=3)

        output_row = ttk.Frame(toolbar)
        output_row.pack(fill="x", pady=2)
        ttk.Label(output_row, text="3) Output:").pack(side="left", padx=(0, 4))
        self.pdf_btn = ttk.Button(output_row, text="Generate Amazon PDF", command=self.generate_amazon_pdf_clicked)
        self.pdf_btn.pack(side="left", padx=3)
        self.prn_btn = ttk.Button(output_row, text="Generate Amazon PRN", command=self.generate_amazon_prn_clicked)
        self.prn_btn.pack(side="left", padx=3)
        self.prn_print_btn = ttk.Button(output_row, text="Generate PRN & Print", command=self.generate_amazon_prn_and_print_clicked)
        self.prn_print_btn.pack(side="left", padx=3)
        ttk.Button(output_row, text="Select Printer", command=self.select_printer_dialog).pack(side="left", padx=3)
        ttk.Button(output_row, text="Print Last PRN", command=self.print_last_prn).pack(side="left", padx=3)

        output_more_row = ttk.Frame(toolbar)
        output_more_row.pack(fill="x", pady=2)
        ttk.Label(output_more_row, text="").pack(side="left", padx=(0, 52))
        ttk.Button(output_more_row, text="Open PRN Folder", command=self.open_prn_folder).pack(side="left", padx=3)
        self.pdf_preview_btn = ttk.Button(output_more_row, text="PDF Preview", command=self.generate_selected_pdf_preview)
        self.pdf_preview_btn.pack(side="left", padx=3)
        ttk.Button(output_more_row, text="Open PDF", command=self.open_last_pdf).pack(side="left", padx=3)
        ttk.Button(output_more_row, text="Open Output Folder", command=self.open_output_folder).pack(side="left", padx=3)

        branch_row = ttk.Frame(toolbar)
        branch_row.pack(fill="x", pady=2)
        ttk.Label(branch_row, text="4) Branch / Layout:").pack(side="left", padx=(0, 4))
        self.branch_combo = ttk.Combobox(branch_row, textvariable=self.branch_var, state="readonly", width=30)
        self.branch_combo.pack(side="left", padx=3)
        self.branch_combo.bind("<<ComboboxSelected>>", self.on_branch_selected)
        self.branch_combo.bind("<Button-1>", lambda _event: self.refresh_branch_list())
        ttk.Label(branch_row, text="PDF Layout:").pack(side="left", padx=(14, 4))
        self.layout_combo = ttk.Combobox(
            branch_row,
            textvariable=self.layout_var,
            state="readonly",
            width=28,
            values=amazon_label_renderer.PDF_LAYOUT_VALUES,
        )
        self.layout_combo.pack(side="left", padx=3)
        self.layout_combo.bind("<<ComboboxSelected>>", self.on_layout_selected)

        status_box = ttk.Frame(self)
        status_box.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Label(status_box, textvariable=self.master_status_var).pack(anchor="w")
        ttk.Label(status_box, textvariable=self.consignment_status_var).pack(anchor="w")
        ttk.Label(status_box, textvariable=self.status_var).pack(anchor="w")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=4, pady=4)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)

        ttk.Label(left, text="Amazon Validation").pack(anchor="w")
        table_frame = ttk.Frame(left)
        table_frame.pack(fill="both", expand=True, pady=(3, 0))
        self.amazon_tree = ttk.Treeview(table_frame, columns=self.TREE_COLS, show="headings", height=22)
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
            "sku": 130,
            "asin": 105,
            "fnsku": 115,
            "title": 230,
            "heading": 120,
            "brand": 110,
            "mrp": 150,
            "qty": 80,
            "error": 250,
        }
        for col in self.TREE_COLS:
            self.amazon_tree.heading(col, text=headings[col])
            self.amazon_tree.column(col, width=widths[col], anchor="w", stretch=True)
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.amazon_tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.amazon_tree.xview)
        self.amazon_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.amazon_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.amazon_tree.tag_configure("pass", foreground="#9FE8A0")
        self.amazon_tree.tag_configure("fail", foreground="#FFB3B3")
        self.amazon_tree.bind("<<TreeviewSelect>>", self.on_row_select)
        self.amazon_tree.bind("<Double-1>", self.quick_set_qty)

        qtybar = ttk.Frame(left)
        qtybar.pack(fill="x", pady=6)
        ttk.Label(qtybar, text="Print Qty selected SKU:").pack(side="left")
        ttk.Entry(qtybar, textvariable=self.qty_var, width=8).pack(side="left", padx=5)
        ttk.Button(qtybar, text="Apply Qty to Selected SKU", command=self.apply_qty_to_selected).pack(side="left", padx=4)

        ttk.Label(right, text="Amazon Label Preview").pack(anchor="w")
        self.preview = tk.Canvas(right, bg="#f4f4f4", highlightthickness=1, highlightbackground="#cccccc")
        self.preview.pack(fill="both", expand=True, padx=6, pady=6)
        self.preview.bind("<Configure>", lambda _event: self.preview_selected(silent=True))

    def refresh_branch_list(self):
        names = list(self.branches().keys())
        self.branch_combo["values"] = names
        if names and self.branch_var.get() not in names:
            configured = self.mapping.get("selected_branch", "")
            self.branch_var.set(configured if configured in names else names[0])
        if names and not self.branch_var.get():
            self.branch_var.set(names[0])

    def branches(self):
        try:
            data = self.branches_provider() or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            log_error(traceback.format_exc())
            return {}

    def current_branch(self):
        branches = self.branches()
        name = self.branch_var.get()
        if name in branches:
            return dict(branches.get(name) or {})
        try:
            current = self.current_branch_provider()
            if current:
                return dict(current)
        except Exception:
            log_error(traceback.format_exc())
        if branches:
            return dict(next(iter(branches.values())))
        return {}

    def on_branch_selected(self, _event=None):
        self.mapping["selected_branch"] = self.branch_var.get()
        try:
            amazon_rules.save_mapping_settings(self.mapping)
        except Exception:
            log_error(traceback.format_exc())
        if self.consignment_df is not None:
            self.rebuild_amazon_rows()

    def selected_pdf_layout(self):
        layout = amazon_label_renderer.normalize_pdf_layout(self.layout_var.get())
        if self.layout_var.get() != layout:
            self.layout_var.set(layout)
        return layout

    def on_layout_selected(self, _event=None):
        self.mapping["pdf_layout"] = self.selected_pdf_layout()
        try:
            amazon_rules.save_mapping_settings(self.mapping)
        except Exception:
            log_error(traceback.format_exc())
        self.preview_selected(silent=True)
        self.set_status(f"Amazon PDF layout set to: {self.layout_var.get()}")

    # ---------------- Background helpers ----------------
    def set_status(self, text):
        self.status_var.set(text)

    def set_buttons_state(self, buttons, state):
        for button in buttons:
            try:
                button.config(state=state)
            except Exception:
                pass

    def run_background(self, buttons, busy_text, worker, done_callback):
        self.set_buttons_state(buttons, "disabled")
        self.set_status(busy_text)

        def runner():
            try:
                result = worker()
            except Exception:
                err = traceback.format_exc()
                log_error(err)
                self.after(0, lambda: self.on_background_error(buttons, err))
            else:
                self.after(0, lambda: self.on_background_done(buttons, done_callback, result))

        threading.Thread(target=runner, daemon=True).start()

    def on_background_done(self, buttons, done_callback, result):
        self.set_buttons_state(buttons, "normal")
        done_callback(result)

    def on_background_error(self, buttons, err):
        self.set_buttons_state(buttons, "normal")
        self.set_status("Amazon task failed. Check marketplace_v12/logs/debug_log.txt")
        messagebox.showerror("Amazon task failed", err)

    # ---------------- File loading ----------------
    def upload_master_file(self):
        path = filedialog.askopenfilename(
            title="Select Weekly Master Listing",
            filetypes=[("Excel Workbook", "*.xlsx *.xls"), ("All Files", "*.*")],
        )
        if not path:
            return

        def worker():
            return amazon_reader.load_master_listing_file(path, self.mapping)

        def done(data):
            self.master_data = data
            self.master_df = data.get("master_df")
            self.master_path = path
            self.mapping["last_master_path"] = path
            try:
                amazon_rules.save_mapping_settings(self.mapping)
            except Exception:
                log_error(traceback.format_exc())
            self.master_status_var.set(
                f"Master Listing: {Path(path).name} | sheet {data.get('master_sheet', '')} | rows {len(self.master_df) if self.master_df is not None else 0}"
            )
            self.set_status("Weekly master listing loaded.")
            if self.consignment_df is not None:
                self.rebuild_amazon_rows()

        self.run_background([self.master_upload_btn], "Loading weekly master listing in background...", worker, done)

    def upload_consignment_file(self):
        path = filedialog.askopenfilename(
            title="Select Amazon Consignment File",
            filetypes=[("Excel Workbook", "*.xlsx *.xls"), ("All Files", "*.*")],
        )
        if not path:
            return

        def worker():
            return amazon_reader.load_consignment_file(path, self.mapping)

        def done(data):
            self.consignment_data = data
            self.consignment_df = data.get("consignment_df")
            self.consignment_path = path
            try:
                amazon_rules.merge_sheet_options(data.get("sheet_categories", []), data.get("sheet_brands", []))
                self.category_rules = amazon_rules.load_category_rules()
                self.brand_rules = amazon_rules.load_brand_rules()
            except Exception:
                log_error(traceback.format_exc())
            self.consignment_status_var.set(
                f"Consignment File: {Path(path).name} | sheet {data.get('consignment_sheet', '')} | rows {len(self.consignment_df) if self.consignment_df is not None else 0}"
            )
            self.set_status("Amazon consignment file loaded.")
            self.rebuild_amazon_rows()

        self.run_background([self.consignment_upload_btn], "Loading Amazon consignment file in background...", worker, done)

    def clear_consignment(self):
        self.consignment_data = None
        self.consignment_df = None
        self.consignment_path = ""
        self.amazon_rows = []
        self.qty_overrides = {}
        self.consignment_status_var.set("Consignment File: not loaded")
        self.populate_tree()
        self.show_empty_preview()
        self.set_status("Amazon consignment cleared.")

    def clear_master(self):
        self.master_data = None
        self.master_df = None
        self.master_path = ""
        self.manual_mrp = {}
        self.mapping["last_master_path"] = ""
        try:
            amazon_rules.save_mapping_settings(self.mapping)
        except Exception:
            log_error(traceback.format_exc())
        self.master_status_var.set("Master Listing: not loaded")
        if self.consignment_df is not None:
            self.rebuild_amazon_rows()
        self.set_status("Weekly master listing cleared.")

    # ---------------- Data and validation ----------------
    def rebuild_amazon_rows(self):
        if self.consignment_df is None:
            self.amazon_rows = []
            self.populate_tree()
            return []
        self.refresh_branch_list()
        self.category_rules = amazon_rules.load_category_rules()
        self.brand_rules = amazon_rules.load_brand_rules()
        self.amazon_rows = amazon_validation.resolve_amazon_rows(
            self.consignment_df,
            self.mapping,
            self.category_rules,
            self.brand_rules,
            manual_mrp=self.manual_mrp,
            qty_overrides=self.qty_overrides,
            master_df=self.master_df,
        )
        amazon_validation.validate_amazon_rows(self.amazon_rows, self.current_branch())
        self.populate_tree()
        return self.amazon_rows

    def populate_tree(self):
        self.tree_item_to_index = {}
        for item in self.amazon_tree.get_children():
            self.amazon_tree.delete(item)
        for index, row in enumerate(self.amazon_rows):
            iid = f"amazon_{index}"
            self.tree_item_to_index[iid] = index
            tag = "pass" if row.get("status") == "PASS" else "fail"
            self.amazon_tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    row.get("status", ""),
                    row.get("merchant_sku", ""),
                    row.get("asin", ""),
                    row.get("fnsku", ""),
                    row.get("title", ""),
                    row.get("main_heading", ""),
                    row.get("brand", ""),
                    amazon_label_renderer.amazon_mrp_for_print(row.get("mrp", "")),
                    row.get("print_qty", ""),
                    "; ".join(row.get("errors", [])),
                ),
                tags=(tag,),
            )
        if self.amazon_rows and not self.amazon_tree.selection():
            first = self.amazon_tree.get_children()[0]
            self.amazon_tree.selection_set(first)
            self.amazon_tree.focus(first)
        self.preview_selected(silent=True)

    def selected_row_index(self):
        selection = self.amazon_tree.selection()
        if not selection:
            return None
        return self.tree_item_to_index.get(selection[0])

    def selected_row(self):
        index = self.selected_row_index()
        if index is None or index < 0 or index >= len(self.amazon_rows):
            return None
        return self.amazon_rows[index]

    def on_row_select(self, _event=None):
        row = self.selected_row()
        if row:
            self.qty_var.set(str(row.get("print_qty", "1")))
        self.preview_selected(silent=True)

    def apply_qty_to_selected(self):
        row = self.selected_row()
        if not row:
            messagebox.showwarning("No selection", "Select an Amazon row first.")
            return
        qty = amazon_validation.parse_positive_int(self.qty_var.get())
        if qty <= 0:
            messagebox.showwarning("Invalid quantity", "Enter a positive print quantity.")
            return
        self.qty_overrides[row.get("row_key")] = qty
        self.rebuild_amazon_rows()
        self.set_status(f"Print quantity set to {qty} for selected Amazon SKU.")

    def quick_set_qty(self, _event=None):
        row = self.selected_row()
        if not row:
            return
        current = amazon_validation.parse_positive_int(row.get("print_qty", 1)) or 1
        qty = simpledialog.askinteger("Print Quantity", "Enter print quantity for selected Amazon SKU:", initialvalue=current, minvalue=1, parent=self)
        if qty:
            self.qty_var.set(str(qty))
            self.apply_qty_to_selected()

    def validate_amazon_clicked(self):
        if self.consignment_df is None:
            messagebox.showwarning("No Amazon consignment", "Upload an Amazon consignment file first.")
            return
        self.rebuild_amazon_rows()
        fail_count = sum(1 for row in self.amazon_rows if row.get("errors"))
        if fail_count:
            self.set_status(f"Amazon validation found {fail_count} blocking row(s).")
            messagebox.showwarning("Amazon validation", f"{fail_count} row(s) have blocking errors. Use Fix Blocking Rows.")
        else:
            self.set_status(f"Amazon validation passed for {len(self.amazon_rows)} row(s).")
            messagebox.showinfo("Amazon validation", "Amazon validation passed.")

    # ---------------- Fix dialog ----------------
    def fix_blocking_rows_dialog(self):
        if self.consignment_df is None:
            messagebox.showwarning("No Amazon consignment", "Upload an Amazon consignment file first.")
            return
        self.rebuild_amazon_rows()
        if not amazon_validation.has_blocking_errors(self.amazon_rows):
            messagebox.showinfo("Amazon validation", "No blocking Amazon rows found.")
            return

        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("Fix Blocking Amazon Rows")
        dlg.geometry("980x560")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ttk.Label(dlg, text="Blocking Amazon Rows", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        body = ttk.Panedwindow(dlg, orient="horizontal")
        body.pack(fill="both", expand=True, padx=12, pady=8)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)

        cols = ("sku", "asin", "fnsku", "title", "missing")
        blocker_tree = ttk.Treeview(left, columns=cols, show="headings", height=18)
        headings = {
            "sku": "SKU",
            "asin": "ASIN",
            "fnsku": "FNSKU",
            "title": "Title",
            "missing": "Missing field",
        }
        widths = {"sku": 130, "asin": 100, "fnsku": 110, "title": 260, "missing": 230}
        for col in cols:
            blocker_tree.heading(col, text=headings[col])
            blocker_tree.column(col, width=widths[col], anchor="w", stretch=True)
        blocker_tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(left, orient="vertical", command=blocker_tree.yview)
        sb.pack(side="right", fill="y")
        blocker_tree.configure(yscrollcommand=sb.set)

        info_var = tk.StringVar(value="")
        category_var = tk.StringVar()
        brand_var = tk.StringVar()
        mrp_var = tk.StringVar()

        ttk.Label(right, textvariable=info_var, wraplength=340, justify="left").pack(anchor="w", pady=(0, 10))
        ttk.Label(right, text="Main Heading").pack(anchor="w")
        category_combo = ttk.Combobox(right, textvariable=category_var, values=self.category_rules.get("categories", []), state="readonly", width=34)
        category_combo.pack(fill="x", pady=(2, 8))
        ttk.Button(right, text="Save Rule / Apply category", command=lambda: apply_category()).pack(anchor="w", pady=(0, 12))

        ttk.Label(right, text="Brand").pack(anchor="w")
        brand_combo = ttk.Combobox(right, textvariable=brand_var, values=self.brand_rules.get("brands", []), state="normal", width=34)
        brand_combo.pack(fill="x", pady=(2, 8))
        ttk.Button(right, text="Save Brand / Apply brand", command=lambda: apply_brand()).pack(anchor="w", pady=(0, 12))

        ttk.Label(right, text="MRP").pack(anchor="w")
        ttk.Entry(right, textvariable=mrp_var, width=36).pack(fill="x", pady=(2, 8))
        ttk.Button(right, text="Apply MRP for this print", command=lambda: apply_mrp()).pack(anchor="w", pady=(0, 12))
        ttk.Label(
            right,
            text="Branch/address errors must be fixed in the Branches & Settings tab.",
            wraplength=340,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

        def refresh_blockers(select_first=True):
            for item in blocker_tree.get_children():
                blocker_tree.delete(item)
            for index, row in enumerate(self.amazon_rows):
                if not row.get("errors"):
                    continue
                blocker_tree.insert(
                    "",
                    "end",
                    iid=str(index),
                    values=(
                        row.get("merchant_sku", ""),
                        row.get("asin", ""),
                        row.get("fnsku", ""),
                        row.get("title", ""),
                        "; ".join(row.get("errors", [])),
                    ),
                )
            children = blocker_tree.get_children()
            if children and select_first:
                blocker_tree.selection_set(children[0])
                blocker_tree.focus(children[0])
                load_selected_blocker()
            if not children:
                dlg.destroy()
                messagebox.showinfo("Amazon validation", "All Amazon blocking rows are fixed.")

        def selected_blocker_row():
            selection = blocker_tree.selection()
            if not selection:
                messagebox.showwarning("No selection", "Select a blocking row first.", parent=dlg)
                return None
            try:
                return self.amazon_rows[int(selection[0])]
            except Exception:
                return None

        def load_selected_blocker(_event=None):
            row = selected_blocker_row()
            if not row:
                return
            info_var.set(
                f"SKU: {row.get('merchant_sku', '')}\n"
                f"ASIN: {row.get('asin', '')}\n"
                f"FNSKU: {row.get('fnsku', '')}\n"
                f"Title: {row.get('title', '')}\n"
                f"Missing field: {'; '.join(row.get('errors', []))}"
            )
            category_var.set(row.get("main_heading", ""))
            brand_var.set(row.get("brand", ""))
            mrp_var.set(row.get("mrp", ""))

        def apply_category():
            row = selected_blocker_row()
            category = amazon_rules.clean_text(category_var.get())
            if not row or not category:
                messagebox.showwarning("Category required", "Select a category first.", parent=dlg)
                return
            amazon_rules.save_category_manual_rule(row, category)
            self.category_rules = amazon_rules.load_category_rules()
            category_combo["values"] = self.category_rules.get("categories", [])
            self.rebuild_amazon_rows()
            refresh_blockers(select_first=False)
            self.set_status("Amazon main heading rule saved and applied.")

        def apply_brand():
            row = selected_blocker_row()
            brand = amazon_rules.clean_text(brand_var.get())
            if not row or not brand:
                messagebox.showwarning("Brand required", "Select or type a brand first.", parent=dlg)
                return
            amazon_rules.save_brand_manual_rule(row, brand)
            self.brand_rules = amazon_rules.load_brand_rules()
            brand_combo["values"] = self.brand_rules.get("brands", [])
            self.rebuild_amazon_rows()
            refresh_blockers(select_first=False)
            self.set_status("Amazon brand rule saved and applied.")

        def apply_mrp():
            row = selected_blocker_row()
            mrp = amazon_validation.normalize_mrp(mrp_var.get())
            if not row or not mrp:
                messagebox.showwarning("MRP required", "Enter a valid MRP for this print.", parent=dlg)
                return
            self.manual_mrp[row.get("row_key")] = mrp
            self.rebuild_amazon_rows()
            refresh_blockers(select_first=False)
            self.set_status("Amazon MRP applied for this print only.")

        blocker_tree.bind("<<TreeviewSelect>>", load_selected_blocker)
        refresh_blockers()

        buttons = ttk.Frame(dlg)
        buttons.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(buttons, text="Close", command=dlg.destroy).pack(side="right")

    # ---------------- Preview ----------------
    def preview_selected(self, silent=False):
        row = self.selected_row()
        if row is None:
            if not silent:
                messagebox.showwarning("No selection", "Select an Amazon row first.")
            self.show_empty_preview()
            return
        self.draw_preview(row)

    def show_empty_preview(self):
        if not hasattr(self, "preview"):
            return
        self.preview.delete("all")
        self.preview.create_text(24, 24, text="Upload Amazon consignment file to preview", anchor="nw", fill="#777777", font=("Arial", 14, "bold"))

    def draw_preview(self, row):
        c = self.preview
        c.delete("all")
        w = max(c.winfo_width(), 420)
        h = max(c.winfo_height(), 420)
        pad = 18
        size = min(w - pad * 2, h - pad * 2)
        x0 = (w - size) / 2
        y0 = (h - size) / 2
        amazon_label_renderer.draw_amazon_label_preview(c, x0, y0, size, row, self.current_branch())

    # ---------------- Generation ----------------
    def prepare_generation(self, output_kind):
        if self.consignment_df is None:
            messagebox.showwarning("No Amazon consignment", "Upload an Amazon consignment file first.")
            return None
        self.rebuild_amazon_rows()
        if amazon_validation.has_blocking_errors(self.amazon_rows):
            self.fix_blocking_rows_dialog()
            self.set_status(f"Amazon {output_kind} blocked until validation issues are fixed.")
            return None
        total = sum(amazon_validation.parse_positive_int(row.get("print_qty", 0)) for row in self.amazon_rows)
        if total <= 0:
            messagebox.showerror("No labels", "Amazon print quantity is zero.")
            return None
        if total > 5000:
            ok = messagebox.askyesno(f"Large Amazon {output_kind}", f"You are generating {total} Amazon labels. Continue?")
            if not ok:
                return None
        return total, copy.deepcopy(self.amazon_rows), copy.deepcopy(self.current_branch())

    def generate_amazon_pdf_clicked(self):
        if amazon_label_renderer.pdfcanvas is None:
            messagebox.showerror("Missing package", "reportlab is missing. Run install_requirements.bat first.")
            return
        prepared = self.prepare_generation("PDF")
        if not prepared:
            return
        total, rows_snapshot, branch = prepared
        layout = self.selected_pdf_layout()
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = output_dir() / f"amazon_labels_{stamp}.pdf"
        report_out = output_dir() / f"amazon_label_report_{stamp}.csv"

        def progress(done, grand_total):
            self.after(0, lambda: self.set_status(f"Generating Amazon PDF... {done}/{grand_total} labels done"))

        def worker():
            amazon_validation.write_report_csv(report_out, rows_snapshot)
            generated = amazon_label_renderer.generate_amazon_pdf(
                out,
                rows_snapshot,
                branch,
                progress_callback=progress,
                layout=layout,
            )
            return generated, str(out), str(report_out)

        def done(result):
            generated, pdf_path, report_path = result
            self.last_pdf = pdf_path
            self.last_report = report_path
            self.record_amazon_output("PDF", pdf_path, report_path, generated)
            self.set_status(f"Amazon PDF generated: {generated} labels -> {pdf_path}")
            messagebox.showinfo("Amazon PDF generated", f"Amazon PDF generated successfully.\n\nLabels: {generated}\nPDF:\n{pdf_path}\n\nReport CSV:\n{report_path}")

        self.run_background([self.pdf_btn], f"Generating {total} Amazon PDF labels in background...", worker, done)

    def generate_amazon_prn_clicked(self):
        self.start_amazon_prn_generation(print_after=False)

    def generate_amazon_prn_and_print_clicked(self):
        self.start_amazon_prn_generation(print_after=True)

    def start_amazon_prn_generation(self, print_after=False):
        prepared = self.prepare_generation("PRN")
        if not prepared:
            return
        total, rows_snapshot, branch = prepared
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = output_dir() / f"amazon_labels_{stamp}.prn"
        report_out = output_dir() / f"amazon_label_report_{stamp}.csv"

        def progress(done, grand_total):
            self.after(0, lambda: self.set_status(f"Generating Amazon PRN... {done}/{grand_total} labels done"))

        def worker():
            amazon_validation.write_report_csv(report_out, rows_snapshot)
            generated = amazon_prn_renderer.generate_amazon_prn(out, rows_snapshot, branch, progress_callback=progress)
            return generated, str(out), str(report_out)

        def done(result):
            generated, prn_path, report_path = result
            self.last_prn = prn_path
            self.last_report = report_path
            self.record_amazon_output("PRN", prn_path, report_path, generated)
            self.set_status(f"Amazon PRN generated: {generated} labels -> {prn_path}")
            if print_after:
                self.print_last_prn()
            else:
                messagebox.showinfo("Amazon PRN generated", f"Amazon PRN generated successfully.\n\nLabels: {generated}\nPRN:\n{prn_path}\n\nReport CSV:\n{report_path}")

        buttons = [self.prn_btn]
        if hasattr(self, "prn_print_btn"):
            buttons.append(self.prn_print_btn)
        self.run_background(buttons, f"Generating {total} Amazon PRN labels in background...", worker, done)

    def generate_selected_pdf_preview(self):
        if amazon_label_renderer.pdfcanvas is None:
            messagebox.showerror("Missing package", "reportlab is missing. Run install_requirements.bat first.")
            return
        row = self.selected_row()
        if not row:
            messagebox.showwarning("No selection", "Select an Amazon row first.")
            return
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = output_dir() / f"amazon_label_preview_{stamp}.pdf"
        row_snapshot = copy.deepcopy(row)
        branch = copy.deepcopy(self.current_branch())
        layout = self.selected_pdf_layout()

        def worker():
            generated = amazon_label_renderer.generate_amazon_pdf_proof(out, row_snapshot, branch, layout=layout)
            return generated, str(out)

        def done(result):
            generated, pdf_path = result
            self.last_pdf = pdf_path
            self.record_amazon_output("PDF Preview", pdf_path, "", generated)
            self.set_status(f"Amazon proof PDF generated -> {pdf_path}")
            self.open_existing_file(pdf_path, "Generate Amazon PDF preview first.")

        self.run_background([self.pdf_preview_btn], "Generating selected Amazon proof PDF...", worker, done)

    def record_amazon_output(self, kind, output_path_value, report_path, total):
        if record_output is None:
            return
        try:
            inputs = [p for p in (self.master_path, self.consignment_path) if p]
            record_output(
                f"Marketplace Product Label Generator V12 + Amazon - {kind}",
                output_path_value,
                "Amazon_Product_Labels",
                "",
                inputs,
                f"{total} Amazon labels; report {report_path}",
            )
        except Exception:
            log_error(traceback.format_exc())

    # ---------------- Open and print ----------------
    def open_last_pdf(self):
        self.open_existing_file(self.last_pdf, "Generate Amazon PDF first.")

    def open_existing_file(self, path, warning):
        if not path or not os.path.exists(path):
            messagebox.showwarning("Missing file", warning)
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror("Open file failed", str(exc))

    def open_folder(self, folder):
        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))
        except Exception as exc:
            messagebox.showerror("Open folder failed", str(exc))

    def open_prn_folder(self):
        if self.last_prn and os.path.exists(self.last_prn):
            self.open_folder(Path(self.last_prn).parent)
        else:
            self.open_folder(output_dir())

    def open_output_folder(self):
        self.open_folder(output_dir())

    def load_selected_printer(self):
        try:
            p = printer_settings_path()
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                return data.get("selected_printer", "")
        except Exception:
            log_error(traceback.format_exc())
        return ""

    def save_selected_printer(self, printer_name):
        try:
            p = printer_settings_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"selected_printer": printer_name or ""}, indent=2), encoding="utf-8")
            self.set_status(f"Amazon printer selected: {printer_name}")
        except Exception:
            log_error(traceback.format_exc())

    def list_windows_printers(self):
        try:
            import win32print
        except Exception:
            return None
        try:
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            names = []
            for item in win32print.EnumPrinters(flags):
                if len(item) >= 3 and item[2]:
                    names.append(item[2])
            return sorted(dict.fromkeys(names))
        except Exception:
            log_error(traceback.format_exc())
            return []

    def select_printer_dialog(self):
        printers = self.list_windows_printers()
        if printers is None:
            messagebox.showinfo(
                "Manual PRN print",
                "pywin32 is missing, so Windows printer selection is not available.\n\nManual command:\n"
                + self.manual_prn_instruction(),
            )
            return

        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("Select Amazon PRN Printer")
        dlg.geometry("560x430")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()
        ttk.Label(dlg, text="Select printer for Amazon PRN labels", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(14, 4))
        ttk.Label(dlg, text="This sends TSPL/PRN commands directly as RAW data.").pack(anchor="w", padx=14, pady=(0, 10))
        frame = ttk.Frame(dlg)
        frame.pack(fill="both", expand=True, padx=14, pady=8)
        lb = tk.Listbox(frame, height=12)
        lb.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, command=lb.yview)
        sb.pack(side="right", fill="y")
        lb.configure(yscrollcommand=sb.set)
        selected = self.load_selected_printer()
        for printer in printers:
            lb.insert("end", printer)
            if printer == selected:
                lb.selection_set("end")
        manual_var = tk.StringVar(value=selected)
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
            dlg.destroy()

        buttons = ttk.Frame(dlg)
        buttons.pack(fill="x", padx=14, pady=(4, 14))
        ttk.Button(buttons, text="Use Selected", command=use_selected).pack(side="left", padx=4)
        ttk.Button(buttons, text="Save Printer", command=save_and_close).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=dlg.destroy).pack(side="right", padx=4)

    def find_tsc_printer(self, win32print):
        try:
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            for item in win32print.EnumPrinters(flags):
                if len(item) >= 3:
                    name = item[2] or ""
                    if "TSC" in name.upper() or "TE244" in name.upper():
                        return name
        except Exception:
            log_error(traceback.format_exc())
        return ""

    def default_printer(self, win32print):
        try:
            return win32print.GetDefaultPrinter() or ""
        except Exception:
            return ""

    def manual_prn_instruction(self):
        if not self.last_prn:
            return 'copy /b "file.prn" "\\\\COMPUTER\\TSC TE244"'
        return f'copy /b "{self.last_prn}" "\\\\COMPUTER\\TSC TE244"'

    def print_last_prn(self):
        if not self.last_prn or not os.path.exists(self.last_prn):
            messagebox.showwarning("No PRN", "Generate Amazon PRN first.")
            return
        try:
            import win32print
        except Exception:
            messagebox.showinfo(
                "Manual PRN print",
                "pywin32 is missing, so direct RAW printing is not available.\n\nManual command:\n"
                + self.manual_prn_instruction(),
            )
            return

        printer = self.load_selected_printer() or self.default_printer(win32print) or self.find_tsc_printer(win32print)
        if not printer:
            messagebox.showinfo(
                "Manual PRN print",
                "No saved or default printer was found.\n\nManual command:\n" + self.manual_prn_instruction(),
            )
            return

        try:
            raw = Path(self.last_prn).read_bytes()
            handle = win32print.OpenPrinter(printer)
            try:
                job = win32print.StartDocPrinter(handle, 1, ("Amazon Labels PRN", None, "RAW"))
                try:
                    win32print.StartPagePrinter(handle)
                    win32print.WritePrinter(handle, raw)
                    win32print.EndPagePrinter(handle)
                finally:
                    win32print.EndDocPrinter(handle)
            finally:
                win32print.ClosePrinter(handle)
            self.set_status(f"Amazon PRN sent directly to printer: {printer}")
            messagebox.showinfo("Print sent", f"Amazon PRN sent directly to printer:\n{printer}\n\nFile:\n{self.last_prn}")
        except Exception as exc:
            log_error(traceback.format_exc())
            messagebox.showerror(
                "Direct PRN print failed",
                "Direct RAW printing failed.\n\nManual command:\n"
                + self.manual_prn_instruction()
                + "\n\nError:\n"
                + str(exc),
            )

    def print_last_prn_direct(self):
        self.print_last_prn()
