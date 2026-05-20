import os
import sys
import fitz
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image, ImageTk

try:
    from output_manager import root_dir, dated_pdf_path, subdir, output_path, record_output
except Exception:
    def root_dir():
        p = Path.home() / "Desktop" / "MMS_Label_Tools_Output"; p.mkdir(parents=True, exist_ok=True); return p
    def subdir(name):
        p = root_dir()/name; p.mkdir(parents=True, exist_ok=True); return p
    def dated_pdf_path(folder, prefix, source_name=""):
        import time
        safe = Path(source_name).stem.replace(' ', '_')[:40] if source_name else ''
        return subdir(folder) / f"{prefix}_{safe}_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
    def output_path(folder, prefix, custom_name="", purpose="", source_name="", ext=".pdf"):
        return dated_pdf_path(folder, prefix, source_name)
    def record_output(*args, **kwargs):
        return None

MM_TO_PT = 72 / 25.4
OUT_W_PT = 100 * MM_TO_PT
OUT_H_PT = 150 * MM_TO_PT
BG = "#0F0F1A"
PANEL = "#16162A"
CARD = "#1E1E32"
BORDER = "#2A2A48"
ACCENT = "#C8A96E"
TEXT = "#F4F1E8"
MUTED = "#A5A5B8"
GREEN = "#4CAF8A"
RED = "#D25555"


def resource_path(*parts):
    base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        c = Path(sys._MEIPASS).joinpath(*parts)
        if c.exists():
            return str(c)
    return str(base.joinpath(*parts))


class LabelCropperFrame(tk.Frame):
    def __init__(self, master, on_back=None):
        super().__init__(master, bg=BG)
        self.on_back = on_back
        self.pdf_paths = []
        self.doc = None
        self.current_path = None
        self.page_index = 0
        self.zoom = 1.5
        self.preview_tk = None
        self.preview_img = None
        self.scale_x = 1
        self.scale_y = 1
        self.selection = None
        self.rect_item = None
        self.drag_start = None
        self.auto_preview_rect = None
        self._build()

    def _btn(self, parent, text, cmd, accent=False):
        bg = ACCENT if accent else CARD
        fg = "#111111" if accent else TEXT
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, activebackground="#E1C987" if accent else "#252540",
                      activeforeground=fg, relief="flat", font=("Segoe UI", 9, "bold"), padx=12, pady=8, cursor="hand2")
        return b

    def _build(self):
        header = tk.Frame(self, bg=PANEL, height=68)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(header, bg=ACCENT, width=5).pack(side="left", fill="y")
        if self.on_back:
            self._btn(header, "← Back", self.on_back).pack(side="left", padx=14, pady=14)
        tk.Label(header, text="Flipkart / Amazon Shipping Label Cropper", bg=PANEL, fg=TEXT, font=("Segoe UI", 17, "bold")).pack(side="left", padx=8)
        tk.Label(header, text="Auto crop all pages • Manual crop one box and apply to all pages", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=16)

        toolbar = tk.Frame(self, bg=BG)
        toolbar.pack(fill="x", padx=16, pady=(12, 8))
        self._btn(toolbar, "Open PDF / PDFs", self.open_pdfs, True).pack(side="left", padx=4)
        self._btn(toolbar, "Auto Crop ALL Pages", self.auto_crop_all, True).pack(side="left", padx=4)
        self._btn(toolbar, "Save Manual Crop PDF", self.manual_crop_all).pack(side="left", padx=4)
        self._btn(toolbar, "Clear Box", self.clear_selection).pack(side="left", padx=4)
        self._btn(toolbar, "Open Output Folder", self.open_output_folder).pack(side="right", padx=4)

        namebar = tk.Frame(self, bg=BG)
        namebar.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(namebar, text="Output name", fg=MUTED, bg=BG, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(4,4))
        self.output_name_var = tk.StringVar(value="")
        tk.Entry(namebar, textvariable=self.output_name_var, width=28, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat").pack(side="left", padx=(0,12), ipady=6)
        tk.Label(namebar, text="Purpose", fg=MUTED, bg=BG, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(4,4))
        self.purpose_var = tk.StringVar(value="Shipping_Label_Crop")
        tk.Entry(namebar, textvariable=self.purpose_var, width=28, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat").pack(side="left", padx=(0,12), ipady=6)
        self.combine_var = tk.BooleanVar(value=True)
        tk.Checkbutton(namebar, text="Combine all PDFs into one output", variable=self.combine_var, bg=BG, fg=TEXT,
                       selectcolor=CARD, activebackground=BG, activeforeground=TEXT, font=("Segoe UI", 9)).pack(side="left", padx=(10, 8))
        self.fill_var = tk.BooleanVar(value=True)
        tk.Checkbutton(namebar, text="Keep scan-safe proportion", variable=self.fill_var, bg=BG, fg=TEXT,
                       selectcolor=CARD, activebackground=BG, activeforeground=TEXT, font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
        tk.Label(namebar, text="Name + purpose + source + date/time", fg=MUTED, bg=BG, font=("Segoe UI", 9)).pack(side="left", padx=10)

        tk.Label(toolbar, text="Zoom", fg=MUTED, bg=BG, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(18,4))
        self.zoom_var = tk.StringVar(value=str(self.zoom))
        zoom = ttk.Combobox(toolbar, textvariable=self.zoom_var, width=5, values=["0.8", "1.0", "1.2", "1.5", "1.8", "2.2", "2.7", "3.0"], state="readonly")
        zoom.pack(side="left")
        zoom.bind("<<ComboboxSelected>>", lambda e: self.set_zoom())
        self._btn(toolbar, "Previous", self.prev_page).pack(side="left", padx=(18,4))
        self._btn(toolbar, "Next", self.next_page).pack(side="left", padx=4)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=PANEL, width=310, highlightthickness=1, highlightbackground=BORDER)
        left.grid(row=0, column=0, sticky="nsw", padx=(0,12))
        left.grid_propagate(False)
        tk.Label(left, text="PDF Batch", bg=PANEL, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(14,6))
        self.file_list = tk.Listbox(left, height=8, bg=CARD, fg=TEXT, selectbackground=ACCENT, selectforeground="#111111", relief="flat", highlightthickness=0, font=("Segoe UI", 9))
        self.file_list.pack(fill="x", padx=14)
        self.file_list.bind("<<ListboxSelect>>", self.on_file_select)
        self.info = tk.StringVar(value="Open a PDF. If PDF has 100 pages, crop will create 100 label pages.")
        tk.Label(left, textvariable=self.info, bg=PANEL, fg=MUTED, wraplength=275, justify="left", font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=12)
        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", padx=14, pady=8)
        instructions = (
            "Manual crop flow:\n"
            "1. Open full Flipkart/Amazon PDF.\n"
            "2. Drag box around ONE label on page 1.\n"
            "3. Click Save Manual Crop PDF.\n"
            "4. Same box is applied to every page.\n\n"
            "Auto crop flow:\n"
            "Click Auto Crop ALL Pages. It detects and crops every page.\n"
            "If 100 pages are inside one PDF, output gets 100 label pages.\n\n"
            "All output goes to Desktop:\nMMS_Label_Tools_Output"
        )
        tk.Label(left, text=instructions, bg=PANEL, fg=TEXT, justify="left", wraplength=275, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=6)
        self.status = tk.StringVar(value="Ready")
        tk.Label(left, textvariable=self.status, bg=CARD, fg=GREEN, wraplength=275, justify="left", font=("Segoe UI", 9, "bold"), padx=10, pady=10).pack(fill="x", padx=14, pady=12)

        viewer = tk.Frame(body, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        viewer.grid(row=0, column=1, sticky="nsew")
        viewer.grid_columnconfigure(0, weight=1)
        viewer.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(viewer, bg="#F4F4F4", cursor="crosshair", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ybar = ttk.Scrollbar(viewer, orient="vertical", command=self.canvas.yview)
        ybar.grid(row=0, column=1, sticky="ns")
        xbar = ttk.Scrollbar(viewer, orient="horizontal", command=self.canvas.xview)
        xbar.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)
        self.canvas.bind("<MouseWheel>", self.mousewheel)

    def open_output_folder(self):
        p = str(subdir("Flipkart_Amazon_Cropped_Labels"))
        try:
            os.startfile(p)
        except Exception:
            messagebox.showinfo("Output folder", p)

    def set_zoom(self):
        try:
            self.zoom = float(self.zoom_var.get())
        except Exception:
            self.zoom = 1.5
        self.render_page()

    def open_pdfs(self):
        paths = filedialog.askopenfilenames(title="Select one or more full order PDFs", filetypes=[("PDF files", "*.pdf")])
        if not paths:
            return
        self.pdf_paths = list(paths)
        self.file_list.delete(0, "end")
        for p in self.pdf_paths:
            self.file_list.insert("end", Path(p).name)
        self.file_list.selection_set(0)
        self.load_pdf(self.pdf_paths[0])

    def load_pdf(self, path):
        try:
            if self.doc:
                self.doc.close()
            self.doc = fitz.open(path)
            self.current_path = path
            self.page_index = 0
            self.selection = None
            self.render_page()
            self.status.set(f"Loaded {Path(path).name}")
        except Exception as e:
            messagebox.showerror("PDF Error", f"Could not open PDF:\n{e}")

    def on_file_select(self, _evt=None):
        sel = self.file_list.curselection()
        if sel:
            self.load_pdf(self.pdf_paths[sel[0]])

    def render_page(self):
        if not self.doc:
            return
        page = self.doc[self.page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom), alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.preview_img = img
        self.preview_tk = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.preview_tk, anchor="nw")
        self.canvas.configure(scrollregion=(0,0,img.width,img.height))
        self.scale_x = page.rect.width / img.width
        self.scale_y = page.rect.height / img.height
        try:
            self.auto_preview_rect = self.detect_label_rect(page)
            r = self.auto_preview_rect
            self.canvas.create_rectangle(r.x0/self.scale_x, r.y0/self.scale_y, r.x1/self.scale_x, r.y1/self.scale_y, outline="#0080ff", width=2, dash=(5, 3))
        except Exception:
            self.auto_preview_rect = None
        if self.selection:
            r=self.selection
            self.rect_item = self.canvas.create_rectangle(r.x0/self.scale_x, r.y0/self.scale_y, r.x1/self.scale_x, r.y1/self.scale_y, outline="red", width=3)
        self.info.set(f"PDF: {Path(self.current_path).name}\nPage: {self.page_index+1} / {len(self.doc)}\nPage size: {page.rect.width:.0f} x {page.rect.height:.0f} pt\n\nBlue dotted box = auto-detected label.\nRed box = your manual selection.")

    def prev_page(self):
        if self.doc and self.page_index > 0:
            self.page_index -= 1; self.render_page()
    def next_page(self):
        if self.doc and self.page_index < len(self.doc)-1:
            self.page_index += 1; self.render_page()
    def mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def start_drag(self, event):
        if not self.doc: return
        x = self.canvas.canvasx(event.x); y = self.canvas.canvasy(event.y)
        self.drag_start = (x,y)
        if self.rect_item: self.canvas.delete(self.rect_item)
        self.rect_item = self.canvas.create_rectangle(x,y,x,y, outline="red", width=3)
    def drag(self, event):
        if not self.drag_start or not self.rect_item: return
        x=self.canvas.canvasx(event.x); y=self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect_item, self.drag_start[0], self.drag_start[1], x,y)
    def end_drag(self, event):
        if not self.drag_start: return
        x1,y1=self.drag_start; x2=self.canvas.canvasx(event.x); y2=self.canvas.canvasy(event.y)
        x1,x2=sorted([x1,x2]); y1,y2=sorted([y1,y2])
        if abs(x2-x1)<20 or abs(y2-y1)<20:
            self.status.set("Selection too small. Drag around the full shipping label."); self.selection=None
        else:
            self.selection = fitz.Rect(x1*self.scale_x, y1*self.scale_y, x2*self.scale_x, y2*self.scale_y)
            self.status.set("Manual box saved. Click Save Manual Crop PDF to apply this box to all pages.")
        self.drag_start=None
    def clear_selection(self):
        self.selection=None; self.render_page(); self.status.set("Manual box cleared.")

    def detect_label_rect(self, page):
        """Detect ONLY the shipping-label box, not the invoice below it.

        Flipkart/E-kart PDFs usually draw the label as a boxed table using many
        thin line segments. Older auto crop was expanding from text and could
        include invoice/billing area. This version first reconstructs the outer
        box from the long top/left/right/bottom border lines.
        """
        pr = page.rect

        # 1) Rebuild the outer label rectangle from vector border lines.
        horizontals = []
        verticals = []
        for d in page.get_drawings():
            r = d.get("rect")
            if not r:
                continue
            r = fitz.Rect(r)
            # Thin horizontal border/table line near the shipping-label area
            if r.width > 140 and r.height <= 2.5 and r.y0 < pr.height * 0.58:
                horizontals.append(r)
            # Thin vertical border/table line near the shipping-label area
            if r.height > 180 and r.width <= 2.5 and r.y0 < pr.height * 0.25 and r.y1 < pr.height * 0.62:
                verticals.append(r)

        if len(horizontals) >= 2 and len(verticals) >= 2:
            # Prefer the main outside verticals. They are tall and close to each other.
            verticals = sorted(verticals, key=lambda r: r.height, reverse=True)[:8]
            xs = sorted(set([round(v.x0, 1) for v in verticals] + [round(v.x1, 1) for v in verticals]))
            best = None
            for i, x0 in enumerate(xs):
                for x1 in xs[i+1:]:
                    w = x1 - x0
                    if not (160 <= w <= 360):
                        continue
                    # Use long vertical border bottom first, otherwise invoice lines below can
                    # make auto-crop too tall.
                    side_vs = [v for v in verticals if abs(v.x0 - x0) < 4 or abs(v.x1 - x1) < 4 or abs(v.x0 - x1) < 4 or abs(v.x1 - x0) < 4]
                    ys = []
                    for h in horizontals:
                        # horizontal line should cross most of the candidate width
                        if h.x0 <= x0 + 8 and h.x1 >= x1 - 8:
                            ys.extend([h.y0, h.y1])
                    if len(ys) >= 2 and len(side_vs) >= 2:
                        top = min(min(v.y0 for v in side_vs), min(ys))
                        bottom = max(v.y1 for v in side_vs)
                        height = bottom - top
                        if 240 <= height <= 430 and top < pr.height * 0.12:
                            area = w * height
                            cand = (area, fitz.Rect(x0, top, x1, bottom))
                            if best is None or cand[0] > best[0]:
                                best = cand
            if best:
                return self.pad_rect(best[1], 1.5, pr)

        # 2) If PDF gives one full rectangle drawing, use it.
        candidates = []
        for d in page.get_drawings():
            r = d.get('rect')
            if not r:
                continue
            r = fitz.Rect(r)
            w, h = r.width, r.height
            if 160 <= w <= 360 and 240 <= h <= 440 and r.y0 < pr.height * 0.15:
                candidates.append(r)
        if candidates:
            return self.pad_rect(max(candidates, key=lambda x: x.width * x.height), 1.5, pr)

        # 3) Text fallback: use only top label keywords, then clamp to realistic box.
        words = page.get_text("words")
        key = []
        for w in words:
            txt = str(w[4]).lower()
            if any(k in txt for k in ["e-kart", "logistics", "ordered", "shipping/customer", "awb", "hbd", "cpd"]):
                if w[1] < pr.height * 0.45:
                    key.append(fitz.Rect(w[:4]))
        if key:
            r = key[0]
            for k in key[1:]:
                r |= k
            # fixed expansion, but do not go below normal label bottom
            left = max(pr.x0, r.x0 - 55)
            right = min(pr.x1, r.x1 + 80)
            top = max(pr.y0, r.y0 - 32)
            bottom = min(pr.y1, top + 355)
            return self.pad_rect(fitz.Rect(left, top, right, bottom), 1.5, pr)

        # 4) Stable Flipkart A4 fallback. This intentionally ends before invoice.
        return fitz.Rect(pr.width * 0.32, pr.height * 0.034, pr.width * 0.68, pr.height * 0.455)

    def pad_rect(self, r, pad, lim):
        return fitz.Rect(max(lim.x0,r.x0-pad), max(lim.y0,r.y0-pad), min(lim.x1,r.x1+pad), min(lim.y1,r.y1+pad))

    def add_cropped_pages(self, out, doc, rect_provider):
        # 100mm x 150mm thermal output. By default we keep scan-safe proportions.
        # Uncheck proportion only when you want the label stretched to fill the page.
        margin = 0.8 * MM_TO_PT
        target = fitz.Rect(margin, margin, OUT_W_PT - margin, OUT_H_PT - margin)
        keep_prop = bool(self.fill_var.get())
        for i, page in enumerate(doc):
            crop = rect_provider(page, i)
            crop = fitz.Rect(max(page.rect.x0, crop.x0), max(page.rect.y0, crop.y0), min(page.rect.x1, crop.x1), min(page.rect.y1, crop.y1))
            if crop.width < 50 or crop.height < 50:
                crop = self.detect_label_rect(page)
            new = out.new_page(width=OUT_W_PT, height=OUT_H_PT)
            new.show_pdf_page(target, doc, i, clip=crop, keep_proportion=keep_prop)

    def create_cropped_pdf_for_doc(self, doc, output_path, rect_provider):
        out = fitz.open()
        self.add_cropped_pages(out, doc, rect_provider)
        out.save(str(output_path), garbage=4, deflate=True)
        out.close()

    def create_combined_cropped_pdf(self, paths, output_path, rect_provider_factory):
        out = fitz.open()
        for path in paths:
            doc = fitz.open(path)
            self.add_cropped_pages(out, doc, rect_provider_factory(path))
            doc.close()
        out.save(str(output_path), garbage=4, deflate=True)
        out.close()

    def auto_crop_all(self):
        if not self.pdf_paths:
            messagebox.showwarning("No PDF", "Open PDF first."); return
        saved=[]
        try:
            if self.combine_var.get():
                source = "Combined_Batch" if len(self.pdf_paths) > 1 else self.pdf_paths[0]
                out = output_path("Flipkart_Amazon_Cropped_Labels", "AUTO_CROPPED", self.output_name_var.get(), self.purpose_var.get(), source, ".pdf")
                self.create_combined_cropped_pdf(self.pdf_paths, out, lambda path: (lambda p,i: self.detect_label_rect(p)))
                saved.append(str(out))
                record_output("Flipkart/Amazon Shipping Label Cropper", out, self.purpose_var.get(), self.output_name_var.get(), list(self.pdf_paths), "Auto crop all pages combined output")
            else:
                for path in self.pdf_paths:
                    doc=fitz.open(path)
                    out=output_path("Flipkart_Amazon_Cropped_Labels", "AUTO_CROPPED", self.output_name_var.get(), self.purpose_var.get(), path, ".pdf")
                    self.create_cropped_pdf_for_doc(doc, out, lambda p,i: self.detect_label_rect(p))
                    doc.close(); saved.append(str(out))
                    record_output("Flipkart/Amazon Shipping Label Cropper", out, self.purpose_var.get(), self.output_name_var.get(), [path], "Auto crop all pages")
        except Exception as e:
            messagebox.showerror("Auto crop error", str(e)); return
        self.status.set(f"Auto crop done. Saved {len(saved)} PDF(s). Every page was cropped.")
        messagebox.showinfo("Done", "Auto cropped all pages successfully.\n\nOutput folder:\n" + str(subdir("Flipkart_Amazon_Cropped_Labels")))

    def manual_crop_all(self):
        if not self.pdf_paths:
            messagebox.showwarning("No PDF", "Open PDF first."); return
        if not self.selection:
            messagebox.showwarning("No Manual Box", "First drag a box around one full label. Then click Save Manual Crop PDF."); return
        base_rect=fitz.Rect(self.selection)
        saved=[]
        try:
            if self.combine_var.get():
                source = "Combined_Batch" if len(self.pdf_paths) > 1 else self.pdf_paths[0]
                out=output_path("Flipkart_Amazon_Cropped_Labels", "MANUAL_CROPPED", self.output_name_var.get(), self.purpose_var.get(), source, ".pdf")
                self.create_combined_cropped_pdf(self.pdf_paths, out, lambda path, r=base_rect: (lambda p,i: r))
                saved.append(str(out))
                record_output("Flipkart/Amazon Shipping Label Cropper", out, self.purpose_var.get(), self.output_name_var.get(), list(self.pdf_paths), "Manual crop same box applied to all pages combined output")
            else:
                for path in self.pdf_paths:
                    doc=fitz.open(path)
                    out=output_path("Flipkart_Amazon_Cropped_Labels", "MANUAL_CROPPED", self.output_name_var.get(), self.purpose_var.get(), path, ".pdf")
                    self.create_cropped_pdf_for_doc(doc, out, lambda p,i,r=base_rect: r)
                    doc.close(); saved.append(str(out))
                    record_output("Flipkart/Amazon Shipping Label Cropper", out, self.purpose_var.get(), self.output_name_var.get(), [path], "Manual crop same box applied to all pages")
        except Exception as e:
            messagebox.showerror("Manual crop error", str(e)); return
        self.status.set(f"Manual crop done. Same box applied to all pages. Saved {len(saved)} PDF(s).")
        messagebox.showinfo("Done", "Manual crop saved successfully. Same selected box applied to every page.\n\nOutput folder:\n" + str(subdir("Flipkart_Amazon_Cropped_Labels")))


class LabelCropperWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Flipkart / Amazon Label Cropper - M Men Style")
        self.geometry("1280x820")
        self.minsize(1050, 700)
        icon=resource_path("assets", "logo.ico")
        if os.path.exists(icon):
            try: self.iconbitmap(icon)
            except Exception: pass
        png=resource_path("assets", "logo.png")
        if os.path.exists(png):
            try:
                im=tk.PhotoImage(file=png); self._mms_icon_img=im; self.iconphoto(True, im)
            except Exception: pass
        LabelCropperFrame(self).pack(fill="both", expand=True)
