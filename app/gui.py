"""
gui.py  v4
Premium dark-theme Tkinter GUI — Amazon Label Generator
Sujal Fashion Works

Tabs:
  1. Generate Labels  — file picker + branch selector + courier selector
  2. Settings         — manage branch profiles + courier list
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import threading
import os
import sys
import uuid
try:
    from output_manager import output_path, record_output
except Exception:
    output_path = None
    def record_output(*args, **kwargs): return None

from app.parser import extract_order_data
from app.label_generator import generate_labels_pdf
from app.database import (
    save_orders_to_csv,
    load_settings, save_settings,
    get_branches, get_couriers,
    save_branch, delete_branch,
    save_couriers, set_last_used, get_last_used,
)


# ─── Colour palette ──────────────────────────────────────────────────────────
BG_MAIN   = "#0F0F1A"
BG_PANEL  = "#16162A"
BG_CARD   = "#1E1E32"
BG_HOVER  = "#252540"
ACCENT    = "#C8A96E"
ACCENT2   = "#9B7B4D"
TEXT_PRI  = "#F0EFE8"
TEXT_SEC  = "#9E9EB8"
TEXT_DIM  = "#5E5E78"
GREEN     = "#4CAF8A"
RED       = "#C94F4F"
BORDER    = "#2A2A48"
SEL_BG    = "#2E2E50"

FONT_H1   = ("Segoe UI", 13, "bold")
FONT_H2   = ("Segoe UI", 10, "bold")
FONT_BODY = ("Segoe UI", 9)
FONT_TINY = ("Segoe UI", 8)
FONT_MONO = ("Consolas", 8)


def _app_folder():
    folder = os.path.join(os.path.expanduser("~"), "Desktop", "MMS_Label_Tools_Output", "Amazon_Packing_Labels")
    os.makedirs(folder, exist_ok=True)
    return folder


# ═════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═════════════════════════════════════════════════════════════════════════════

class LabelApp(tk.Frame):

    def __init__(self, master=None, embedded=False, on_back=None):
        self._standalone = master is None
        self.root_window = tk.Tk() if master is None else master
        super().__init__(self.root_window, bg=BG_MAIN)
        self.embedded = embedded
        self.on_back = on_back
        if self._standalone:
            self.pack(fill="both", expand=True)
        root = self.winfo_toplevel()
        try: root.title("Amazon Label Generator — Sujal Fashion Works")
        except Exception: pass
        try: root.geometry("1100x760")
        except Exception: pass
        try: root.minsize(900, 620)
        except Exception: pass
        try: root.configure(bg=BG_MAIN)
        except Exception: pass
        try: root.resizable(True, True)
        except Exception: pass
        self.configure(bg=BG_MAIN)

        self.pdf_files     = []
        self.last_pdf_path = None
        self.last_csv_path = None

        icon_path = self._asset("logo.ico")
        if os.path.exists(icon_path):
            try:
                self.winfo_toplevel().iconbitmap(icon_path)
            except Exception:
                pass

        self._apply_styles()
        self._build_ui()

    def _asset(self, name):
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
        else:
            base = os.path.abspath(".")
        return os.path.join(base, "assets", name)

    def _apply_styles(self):
        style = ttk.Style()
        style.theme_use("default")

        style.configure("TNotebook",
                        background=BG_MAIN, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=BG_PANEL,
                        foreground=TEXT_SEC,
                        font=("Segoe UI", 9, "bold"),
                        padding=[16, 8],
                        borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", BG_CARD)],
                  foreground=[("selected", ACCENT)])

        style.configure("Vertical.TScrollbar",
                        background=BG_HOVER,
                        troughcolor=BG_PANEL,
                        arrowcolor=TEXT_DIM,
                        bordercolor=BORDER)
        style.configure("gold.Horizontal.TProgressbar",
                        troughcolor=BG_PANEL,
                        background=ACCENT,
                        thickness=3)

    # ──────────────────────────────────────────────
    # UI BUILDER
    # ──────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        # Tab 1 — Generate
        self.tab_gen = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_gen, text="  ⚡  GENERATE LABELS  ")

        # Tab 2 — Settings
        self.tab_settings = tk.Frame(self.notebook, bg=BG_MAIN)
        self.notebook.add(self.tab_settings, text="  ⚙  SETTINGS  ")

        self._build_generate_tab(self.tab_gen)
        self._build_settings_tab(self.tab_settings)
        self._build_status_bar()

    # ── Header ─────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_PANEL, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Frame(hdr, bg=ACCENT, width=4).pack(side="left", fill="y")
        if self.on_back:
            tk.Button(hdr, text="← Back", command=self.on_back, bg=BG_HOVER, fg=TEXT_PRI,
                      activebackground=ACCENT2, activeforeground="#0F0F1A", relief="flat",
                      font=FONT_TINY, padx=10, pady=4, cursor="hand2").pack(side="left", padx=(12, 4))
        tk.Label(hdr, text="AMAZON LABEL GENERATOR",
                 font=("Segoe UI", 12, "bold"),
                 fg=TEXT_PRI, bg=BG_PANEL).pack(side="left", padx=16)
        tk.Label(hdr, text="SUJAL FASHION WORKS",
                 font=("Segoe UI", 8),
                 fg=ACCENT, bg=BG_PANEL).pack(side="right", padx=20)

    # ── Status bar ─────────────────────────────────────────────
    def _build_status_bar(self):
        bar = tk.Frame(self, bg=BG_PANEL, height=26)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self.status_var = tk.StringVar(value="Ready — add Amazon packing slip PDFs to begin")
        tk.Label(bar, textvariable=self.status_var,
                 font=FONT_TINY, fg=TEXT_SEC, bg=BG_PANEL).pack(side="left", padx=14)

    # ══════════════════════════════════════════════
    # TAB 1 — GENERATE
    # ══════════════════════════════════════════════

    def _build_generate_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        pad = {"padx": 16, "pady": (10, 0)}

        # ── Selector row: Branch + Courier ────────
        sel_card = tk.Frame(parent, bg=BG_CARD)
        sel_card.grid(row=0, column=0, sticky="ew", **pad)
        sel_card.columnconfigure(1, weight=1)
        sel_card.columnconfigure(3, weight=1)

        tk.Label(sel_card, text="BRANCH / BRAND",
                 font=FONT_TINY, fg=ACCENT, bg=BG_CARD).grid(
            row=0, column=0, padx=(14, 6), pady=(10, 2), sticky="w")
        tk.Label(sel_card, text="COURIER PARTNER",
                 font=FONT_TINY, fg=ACCENT, bg=BG_CARD).grid(
            row=0, column=2, padx=(20, 6), pady=(10, 2), sticky="w")

        # Branch dropdown
        self._branch_var = tk.StringVar()
        self._branch_combo = ttk.Combobox(
            sel_card, textvariable=self._branch_var,
            state="readonly", font=FONT_BODY,
            width=28,
        )
        self._branch_combo.grid(row=1, column=0, columnspan=2,
                                padx=(14, 6), pady=(0, 12), sticky="ew")
        self._style_combo(self._branch_combo)

        # Courier dropdown
        self._courier_var = tk.StringVar()
        self._courier_combo = ttk.Combobox(
            sel_card, textvariable=self._courier_var,
            state="readonly", font=FONT_BODY,
            width=22,
        )
        self._courier_combo.grid(row=1, column=2, columnspan=2,
                                 padx=(6, 14), pady=(0, 12), sticky="ew")
        self._style_combo(self._courier_combo)

        self._refresh_selectors()

        # ── File input ────────────────────────────
        file_card = tk.Frame(parent, bg=BG_CARD)
        file_card.grid(row=1, column=0, sticky="ew",
                       padx=16, pady=(8, 0))

        title_bar = tk.Frame(file_card, bg=BG_CARD)
        title_bar.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(title_bar, text="INPUT FILES",
                 font=FONT_H2, fg=ACCENT, bg=BG_CARD).pack(side="left")
        self._file_count_var = tk.StringVar(value="0 files")
        tk.Label(title_bar, textvariable=self._file_count_var,
                 font=FONT_TINY, fg=TEXT_SEC, bg=BG_CARD).pack(side="right")

        btn_row = tk.Frame(file_card, bg=BG_CARD)
        btn_row.pack(fill="x", padx=14, pady=(0, 6))
        self._btn(btn_row, "Add PDFs", self._add_files,
                  bg=ACCENT, fg="#0F0F1A").pack(side="left", padx=(0, 8))
        self._btn(btn_row, "Clear All", self._clear_files,
                  bg=BG_HOVER, fg=TEXT_SEC).pack(side="left")

        list_frame = tk.Frame(file_card, bg=BG_CARD)
        list_frame.pack(fill="x", padx=14, pady=(0, 8))
        self.file_list = tk.Listbox(
            list_frame, height=4,
            bg=BG_PANEL, fg=TEXT_PRI,
            selectbackground=ACCENT2, selectforeground=TEXT_PRI,
            font=FONT_MONO, relief="flat", bd=0,
            activestyle="none",
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.file_list.pack(fill="x", side="left", expand=True)
        sb = ttk.Scrollbar(list_frame, orient="vertical",
                           command=self.file_list.yview)
        sb.pack(side="right", fill="y")
        self.file_list.configure(yscrollcommand=sb.set)

        gen_frame = tk.Frame(file_card, bg=BG_CARD)
        gen_frame.pack(fill="x", padx=14, pady=(0, 14))
        self.gen_btn = tk.Button(
            gen_frame, text="GENERATE LABELS",
            font=("Segoe UI", 10, "bold"),
            fg="#0F0F1A", bg=ACCENT,
            activebackground=ACCENT2, activeforeground="#0F0F1A",
            relief="flat", bd=0, cursor="hand2", pady=9,
            command=self._start_generate,
        )
        self.gen_btn.pack(fill="x")

        self.progress_var = tk.IntVar(value=0)
        self.progress = ttk.Progressbar(
            gen_frame, variable=self.progress_var,
            mode="indeterminate", length=200,
            style="gold.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x", pady=(5, 0))

        # ── Output / Log ──────────────────────────
        out_card = tk.Frame(parent, bg=BG_CARD)
        out_card.grid(row=2, column=0, sticky="nsew",
                      padx=16, pady=(8, 14))

        title_bar2 = tk.Frame(out_card, bg=BG_CARD)
        title_bar2.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(title_bar2, text="OUTPUT",
                 font=FONT_H2, fg=ACCENT, bg=BG_CARD).pack(side="left")

        btn_row2 = tk.Frame(out_card, bg=BG_CARD)
        btn_row2.pack(fill="x", padx=14, pady=(0, 8))
        self._btn(btn_row2, "Open Labels PDF", self._open_pdf,
                  bg=GREEN, fg="#0F0F1A").pack(side="left", padx=(0, 8))
        self._btn(btn_row2, "Open Orders CSV", self._open_csv,
                  bg=BG_HOVER, fg=TEXT_SEC).pack(side="left", padx=(0, 8))
        self._btn(btn_row2, "Open Folder", self._open_folder,
                  bg=BG_HOVER, fg=TEXT_SEC).pack(side="left")

        log_frame = tk.Frame(out_card, bg=BG_CARD)
        log_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.log_box = tk.Text(
            log_frame, bg=BG_PANEL, fg=TEXT_PRI, font=FONT_MONO,
            relief="flat", bd=0, wrap="word", state="disabled",
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.log_box.pack(side="left", fill="both", expand=True)
        log_sb = ttk.Scrollbar(log_frame, orient="vertical",
                               command=self.log_box.yview)
        log_sb.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=log_sb.set)
        self.log_box.tag_config("ok",    foreground=GREEN)
        self.log_box.tag_config("err",   foreground=RED)
        self.log_box.tag_config("info",  foreground=TEXT_SEC)
        self.log_box.tag_config("gold",  foreground=ACCENT)
        self.log_box.tag_config("white", foreground=TEXT_PRI)

    # ══════════════════════════════════════════════
    # TAB 2 — SETTINGS
    # ══════════════════════════════════════════════

    def _build_settings_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=3)
        parent.rowconfigure(1, weight=1)

        pad = {"padx": 16, "pady": (10, 0)}

        # ── Branch profiles ───────────────────────
        branch_card = tk.Frame(parent, bg=BG_CARD)
        branch_card.grid(row=0, column=0, sticky="nsew", **pad)
        branch_card.columnconfigure(0, weight=1)
        branch_card.rowconfigure(1, weight=1)

        th = tk.Frame(branch_card, bg=BG_CARD)
        th.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        tk.Label(th, text="BRANCH / BRAND PROFILES",
                 font=FONT_H2, fg=ACCENT, bg=BG_CARD).pack(side="left")
        self._btn(th, "+ New Branch", self._new_branch,
                  bg=ACCENT, fg="#0F0F1A").pack(side="right")

        # Branch list + form side by side
        panes = tk.Frame(branch_card, bg=BG_CARD)
        panes.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        panes.columnconfigure(0, weight=1)
        panes.columnconfigure(1, weight=2)
        panes.rowconfigure(0, weight=1)

        # Left: list
        lf = tk.Frame(panes, bg=BG_PANEL,
                      highlightthickness=1, highlightbackground=BORDER)
        lf.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.branch_listbox = tk.Listbox(
            lf, bg=BG_PANEL, fg=TEXT_PRI,
            selectbackground=ACCENT2, selectforeground=TEXT_PRI,
            font=FONT_BODY, relief="flat", bd=0,
            activestyle="none",
            highlightthickness=0,
        )
        self.branch_listbox.pack(fill="both", expand=True, padx=4, pady=4)
        self.branch_listbox.bind("<<ListboxSelect>>", self._on_branch_select)

        # Right: form
        ff = tk.Frame(panes, bg=BG_CARD)
        ff.grid(row=0, column=1, sticky="nsew")
        ff.columnconfigure(1, weight=1)

        fields = [
            ("Branch Name",  "branch_name"),
            ("Brand Name",   "brand_name"),
            ("Logo Path",    "logo_path"),
        ]
        self._branch_entries = {}
        for row_i, (label, key) in enumerate(fields):
            tk.Label(ff, text=label + ":", font=FONT_TINY,
                     fg=TEXT_SEC, bg=BG_CARD, anchor="w").grid(
                row=row_i, column=0, sticky="w",
                padx=(0, 8), pady=(4, 2))

            if key == "logo_path":
                logo_row = tk.Frame(ff, bg=BG_CARD)
                logo_row.grid(row=row_i, column=1, sticky="ew", pady=(4, 2))
                logo_row.columnconfigure(0, weight=1)
                ent = tk.Entry(logo_row, bg=BG_PANEL, fg=TEXT_PRI,
                               insertbackground=ACCENT, relief="flat",
                               font=FONT_BODY,
                               highlightthickness=1,
                               highlightbackground=BORDER,
                               highlightcolor=ACCENT)
                ent.grid(row=0, column=0, sticky="ew", padx=(0, 4))
                self._btn(logo_row, "Browse", lambda: self._browse_logo(),
                          bg=BG_HOVER, fg=TEXT_SEC).grid(row=0, column=1)
                self._branch_entries[key] = ent
            else:
                ent = tk.Entry(ff, bg=BG_PANEL, fg=TEXT_PRI,
                               insertbackground=ACCENT, relief="flat",
                               font=FONT_BODY,
                               highlightthickness=1,
                               highlightbackground=BORDER,
                               highlightcolor=ACCENT)
                ent.grid(row=row_i, column=1, sticky="ew", pady=(4, 2))
                self._branch_entries[key] = ent

        # Address (multiline)
        tk.Label(ff, text="From Address:", font=FONT_TINY,
                 fg=TEXT_SEC, bg=BG_CARD, anchor="w").grid(
            row=len(fields), column=0, sticky="nw", padx=(0, 8), pady=(4, 2))
        self._addr_text = tk.Text(
            ff, height=5,
            bg=BG_PANEL, fg=TEXT_PRI,
            insertbackground=ACCENT, relief="flat", font=FONT_BODY,
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self._addr_text.grid(row=len(fields), column=1,
                             sticky="ew", pady=(4, 2))

        # Save / Delete buttons
        btn_r = tk.Frame(ff, bg=BG_CARD)
        btn_r.grid(row=len(fields)+1, column=0, columnspan=2,
                   sticky="ew", pady=(8, 0))
        self._btn(btn_r, "Save Branch", self._save_branch_form,
                  bg=GREEN, fg="#0F0F1A").pack(side="left", padx=(0, 8))
        self._btn(btn_r, "Delete Branch", self._delete_branch,
                  bg=RED, fg=TEXT_PRI).pack(side="left")

        self._editing_branch_id = None
        self._refresh_branch_list()

        # ── Courier list ──────────────────────────
        cour_card = tk.Frame(parent, bg=BG_CARD)
        cour_card.grid(row=1, column=0, sticky="nsew",
                       padx=16, pady=(8, 14))
        cour_card.columnconfigure(0, weight=1)

        ch = tk.Frame(cour_card, bg=BG_CARD)
        ch.pack(fill="x", padx=14, pady=(10, 6))
        tk.Label(ch, text="COURIER PARTNERS",
                 font=FONT_H2, fg=ACCENT, bg=BG_CARD).pack(side="left")

        cour_row = tk.Frame(cour_card, bg=BG_CARD)
        cour_row.pack(fill="x", padx=14, pady=(0, 10))
        cour_row.columnconfigure(0, weight=1)

        self._new_courier_var = tk.StringVar()
        ce = tk.Entry(cour_row, textvariable=self._new_courier_var,
                      bg=BG_PANEL, fg=TEXT_PRI,
                      insertbackground=ACCENT, relief="flat",
                      font=FONT_BODY,
                      highlightthickness=1,
                      highlightbackground=BORDER,
                      highlightcolor=ACCENT)
        ce.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._btn(cour_row, "+ Add", self._add_courier,
                  bg=ACCENT, fg="#0F0F1A").grid(row=0, column=1)
        self._btn(cour_row, "Remove Selected", self._remove_courier,
                  bg=RED, fg=TEXT_PRI).grid(row=0, column=2, padx=(6, 0))

        cf = tk.Frame(cour_card, bg=BG_PANEL,
                      highlightthickness=1, highlightbackground=BORDER)
        cf.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self.courier_listbox = tk.Listbox(
            cf, height=4,
            bg=BG_PANEL, fg=TEXT_PRI,
            selectbackground=ACCENT2, selectforeground=TEXT_PRI,
            font=FONT_BODY, relief="flat", bd=0,
            activestyle="none", highlightthickness=0,
        )
        self.courier_listbox.pack(fill="both", expand=True, padx=4, pady=4)
        self._refresh_courier_list()

    # ──────────────────────────────────────────────
    # SELECTOR HELPERS
    # ──────────────────────────────────────────────

    def _style_combo(self, combo):
        style = ttk.Style()
        style.configure("TCombobox",
                        fieldbackground=BG_PANEL,
                        background=BG_HOVER,
                        foreground=TEXT_PRI,
                        selectbackground=ACCENT2,
                        selectforeground=TEXT_PRI,
                        bordercolor=BORDER,
                        arrowcolor=ACCENT)

    def _refresh_selectors(self):
        branches = get_branches()
        couriers = get_couriers()
        last_bid, last_cou = get_last_used()

        branch_labels = [f"{b['branch_name']}  —  {b['brand_name']}" for b in branches]
        self._branch_combo["values"] = branch_labels
        self._branches_data = branches

        if branch_labels:
            # Try to restore last used
            idx = 0
            for i, b in enumerate(branches):
                if b.get("id") == last_bid:
                    idx = i
                    break
            self._branch_combo.current(idx)

        self._courier_combo["values"] = couriers
        if couriers:
            if last_cou in couriers:
                self._courier_combo.set(last_cou)
            else:
                self._courier_combo.current(0)

    def _get_selected_branch(self):
        idx = self._branch_combo.current()
        if idx < 0 or not self._branches_data:
            return None
        return self._branches_data[idx]

    def _get_selected_courier(self):
        return self._courier_var.get().strip()

    # ──────────────────────────────────────────────
    # BRANCH LIST MANAGEMENT
    # ──────────────────────────────────────────────

    def _refresh_branch_list(self):
        self.branch_listbox.delete(0, "end")
        for b in get_branches():
            self.branch_listbox.insert(
                "end",
                f"  {b['branch_name']}  |  {b['brand_name']}"
            )
        self._refresh_selectors()

    def _on_branch_select(self, event):
        sel = self.branch_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        branches = get_branches()
        if idx >= len(branches):
            return
        b = branches[idx]
        self._editing_branch_id = b.get("id")
        self._branch_entries["branch_name"].delete(0, "end")
        self._branch_entries["branch_name"].insert(0, b.get("branch_name", ""))
        self._branch_entries["brand_name"].delete(0, "end")
        self._branch_entries["brand_name"].insert(0, b.get("brand_name", ""))
        self._branch_entries["logo_path"].delete(0, "end")
        self._branch_entries["logo_path"].insert(0, b.get("logo_path", ""))
        self._addr_text.delete("1.0", "end")
        self._addr_text.insert("1.0", b.get("address", ""))

    def _new_branch(self):
        self._editing_branch_id = None
        for key, ent in self._branch_entries.items():
            ent.delete(0, "end")
        self._addr_text.delete("1.0", "end")
        self.branch_listbox.selection_clear(0, "end")

    def _save_branch_form(self):
        bname = self._branch_entries["branch_name"].get().strip()
        brand = self._branch_entries["brand_name"].get().strip()
        logo  = self._branch_entries["logo_path"].get().strip()
        addr  = self._addr_text.get("1.0", "end").strip()

        if not bname or not brand:
            messagebox.showwarning("Missing Info", "Branch Name and Brand Name are required.")
            return

        branch_id = self._editing_branch_id or f"branch_{uuid.uuid4().hex[:8]}"
        save_branch({
            "id": branch_id,
            "branch_name": bname,
            "brand_name":  brand,
            "logo_path":   logo,
            "address":     addr,
        })
        self._editing_branch_id = branch_id
        self._refresh_branch_list()
        messagebox.showinfo("Saved", f"Branch '{bname}' saved.")

    def _delete_branch(self):
        if not self._editing_branch_id:
            messagebox.showwarning("Select Branch", "Select a branch to delete.")
            return
        if messagebox.askyesno("Delete", "Delete this branch profile?"):
            delete_branch(self._editing_branch_id)
            self._editing_branch_id = None
            for key, ent in self._branch_entries.items():
                ent.delete(0, "end")
            self._addr_text.delete("1.0", "end")
            self._refresh_branch_list()

    def _browse_logo(self):
        path = filedialog.askopenfilename(
            title="Select Logo Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.ico *.bmp")]
        )
        if path:
            self._branch_entries["logo_path"].delete(0, "end")
            self._branch_entries["logo_path"].insert(0, path)

    # ──────────────────────────────────────────────
    # COURIER MANAGEMENT
    # ──────────────────────────────────────────────

    def _refresh_courier_list(self):
        self.courier_listbox.delete(0, "end")
        for c in get_couriers():
            self.courier_listbox.insert("end", f"  {c}")
        self._refresh_selectors()

    def _add_courier(self):
        name = self._new_courier_var.get().strip()
        if not name:
            return
        couriers = get_couriers()
        if name not in couriers:
            couriers.append(name)
            save_couriers(couriers)
            self._refresh_courier_list()
            self._new_courier_var.set("")

    def _remove_courier(self):
        sel = self.courier_listbox.curselection()
        if not sel:
            return
        couriers = get_couriers()
        idx = sel[0]
        if idx < len(couriers):
            couriers.pop(idx)
            save_couriers(couriers)
            self._refresh_courier_list()

    # ──────────────────────────────────────────────
    # FILE MANAGEMENT
    # ──────────────────────────────────────────────

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="Select Amazon Packing Slip PDFs",
            filetypes=[("PDF Files", "*.pdf")]
        )
        added = 0
        for f in files:
            if f not in self.pdf_files:
                self.pdf_files.append(f)
                self.file_list.insert("end", f"  {os.path.basename(f)}")
                added += 1
        self._file_count_var.set(
            f"{len(self.pdf_files)} file{'s' if len(self.pdf_files) != 1 else ''}"
        )
        if added:
            self._log(f"Added {added} file(s).", tag="info")
        self.status_var.set(f"{len(self.pdf_files)} PDFs loaded — click Generate Labels")

    def _clear_files(self):
        self.pdf_files.clear()
        self.file_list.delete(0, "end")
        self._file_count_var.set("0 files")
        self.status_var.set("Cleared — add PDFs to begin")
        self._log("File list cleared.", tag="info")

    # ──────────────────────────────────────────────
    # GENERATION
    # ──────────────────────────────────────────────

    def _start_generate(self):
        if not self.pdf_files:
            messagebox.showwarning("No Files",
                "Please add Amazon packing slip PDFs first.")
            return

        branch = self._get_selected_branch()
        courier = self._get_selected_courier()

        if not branch:
            messagebox.showwarning("No Branch",
                "Please select a Branch/Brand profile.\n"
                "Add one in the Settings tab first.")
            return
        if not courier:
            messagebox.showwarning("No Courier",
                "Please select a Courier Partner.")
            return

        # Save last used
        set_last_used(branch_id=branch.get("id"), courier=courier)

        self.gen_btn.configure(state="disabled", bg=ACCENT2,
                               text="Processing...")
        self.progress.start(12)
        self.status_var.set("Processing PDFs...")
        self._log("─" * 52, tag="info")
        self._log(
            f"Branch: {branch['branch_name']}  |  Brand: {branch['brand_name']}  |  Courier: {courier}",
            tag="gold"
        )
        self._log(f"Processing {len(self.pdf_files)} PDF(s)...", tag="gold")

        threading.Thread(
            target=self._process,
            args=(branch, courier),
            daemon=True
        ).start()

    def _process(self, branch, courier):
        orders = []
        errors = []

        for i, fpath in enumerate(self.pdf_files, 1):
            fname = os.path.basename(fpath)
            self._ui(lambda f=fname, n=i: self.status_var.set(
                f"Parsing {n}/{len(self.pdf_files)}: {f}"))
            try:
                order = extract_order_data(fpath)
                # Inject branch + courier info
                order['branch_name']      = branch.get('branch_name', '')
                order['brand_name']       = branch.get('brand_name', '')
                order['branch_logo_path'] = branch.get('logo_path', '')
                order['from_address']     = branch.get('address', '')
                order['courier']          = courier
                orders.append(order)
                oid  = order.get('order_id', fname)
                name = order.get('ship_name', '?')
                self._log(f"OK  {oid}  →  {name}", tag="ok")
            except Exception as e:
                errors.append(fname)
                self._log(f"ERR {fname}: {e}", tag="err")

        if not orders:
            self._ui(lambda: messagebox.showerror(
                "Parse Failed",
                "No orders could be extracted.\n"
                "Check that you are using Amazon packing slip PDFs."
            ))
            self._done()
            return

        folder   = _app_folder()
        if output_path:
            pdf_path = str(output_path("Amazon_Packing_Labels", "AMAZON_LABELS", "", "Packing_Slip_Labels", "batch", ".pdf"))
            csv_out  = str(output_path("Amazon_Packing_Labels", "AMAZON_ORDERS", "", "Latest_Run", "batch", ".csv"))
        else:
            pdf_path = os.path.join(folder, "labels.pdf")
            csv_out  = os.path.join(folder, "orders.csv")
        # Do not disturb this tool's existing Excel/CSV database logic.
        csv_db   = os.path.join(folder, "orders_database.csv")

        try:
            generate_labels_pdf(orders, pdf_path)
            self._log(f"Labels PDF saved: {pdf_path}", tag="gold")
        except Exception as e:
            self._log(f"PDF generation error: {e}", tag="err")
            self._done()
            return

        try:
            save_orders_to_csv(orders, csv_out, overwrite=True)
            save_orders_to_csv(orders, csv_db, overwrite=False)
            self._log(f"Database updated: {csv_db}", tag="info")
        except Exception as e:
            self._log(f"CSV error: {e}", tag="err")

        try:
            record_output("Amazon Packing Slip Label Generator", pdf_path, "Packing_Slip_Labels", "", list(self.pdf_files), f"{len(orders)} labels")
            record_output("Amazon Packing Slip Label Generator", csv_out, "Latest_Run_Orders_CSV", "", list(self.pdf_files), f"{len(orders)} orders")
        except Exception:
            pass

        self.last_pdf_path = pdf_path
        self.last_csv_path = csv_out

        summary = (
            f"\nDone — {len(orders)} label(s) generated"
            + (f", {len(errors)} skipped" if errors else "")
        )
        self._log(summary, tag="white")
        self._ui(lambda: self.status_var.set(
            f"Done — {len(orders)} label(s) ready in SujalLabelApp on Desktop"
        ))
        self._done()

    def _done(self):
        self._ui(lambda: [
            self.progress.stop(),
            self.gen_btn.configure(
                state="normal", bg=ACCENT, text="GENERATE LABELS")
        ])

    # ──────────────────────────────────────────────
    # OPEN FILE / FOLDER
    # ──────────────────────────────────────────────

    def _open_pdf(self):
        if not self.last_pdf_path or not os.path.exists(self.last_pdf_path):
            messagebox.showinfo("Not Ready", "Generate labels first.")
            return
        self._open_path(self.last_pdf_path)

    def _open_csv(self):
        if not self.last_csv_path or not os.path.exists(self.last_csv_path):
            messagebox.showinfo("Not Ready", "Generate labels first.")
            return
        self._open_path(self.last_csv_path)

    def _open_folder(self):
        self._open_path(_app_folder())

    def _open_path(self, path):
        try:
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ──────────────────────────────────────────────
    # LOG + UI HELPERS
    # ──────────────────────────────────────────────

    def _log(self, message, tag="white"):
        def _do():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", message + "\n", tag)
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self._ui(_do)

    def _ui(self, fn):
        self.after(0, fn)

    def _btn(self, parent, text, command, bg=BG_HOVER, fg=TEXT_PRI):
        return tk.Button(
            parent, text=text, font=FONT_TINY,
            fg=fg, bg=bg,
            activebackground=ACCENT2, activeforeground="#0F0F1A",
            relief="flat", bd=0, padx=12, pady=5,
            cursor="hand2", command=command,
        )