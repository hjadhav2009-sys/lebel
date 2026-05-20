import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from output_manager import root_dir

def set_windows_app_id():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MMS.Label.Tools.v7")
        except Exception:
            pass

APP_TITLE = "M Men Style Label Tools"
ACCENT = "#C8A96E"
BG = "#0F0F1A"
PANEL = "#16162A"
CARD = "#1E1E32"
BORDER = "#2A2A48"
TEXT = "#F4F1E8"
MUTED = "#A5A5B8"
GREEN = "#4CAF8A"
RED = "#C94F4F"


def base_dir():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def resource_path(*parts):
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        c = Path(sys._MEIPASS).joinpath(*parts)
        if c.exists(): return str(c)
    return str(base_dir().joinpath(*parts))


def apply_icon(win):
    icon = resource_path("assets", "logo.ico")
    png = resource_path("assets", "logo.png")
    if os.path.exists(icon):
        try: win.iconbitmap(icon)
        except Exception: pass
    if os.path.exists(png):
        try:
            img = tk.PhotoImage(file=png)
            win._mms_icon_img = img
            win.iconphoto(True, img)
        except Exception:
            pass


def restart_dashboard(current=None):
    try:
        if current: current.destroy()
    except Exception:
        pass
    app = Dashboard()
    app.mainloop()


def add_back_menu(win):
    try:
        menu = tk.Menu(win)
        nav = tk.Menu(menu, tearoff=0)
        nav.add_command(label="← Back to Dashboard", command=lambda: restart_dashboard(win))
        nav.add_separator()
        nav.add_command(label="Open Central Output Folder", command=open_output_folder)
        nav.add_command(label="Exit", command=win.destroy)
        menu.add_cascade(label="Navigation", menu=nav)
        win.config(menu=menu)
    except Exception:
        pass


def open_output_folder():
    p = str(root_dir())
    try: os.startfile(p)
    except Exception: messagebox.showinfo("Central Output Folder", p)


# tools are embedded into the same root window; no second EXE/window is opened


class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE + " - Dashboard")
        self.geometry("1180x760")
        self.minsize(980, 650)
        self.configure(bg=BG)
        apply_icon(self)
        root_dir()
        self.show_dashboard()

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def button(self, parent, text, cmd, accent=False):
        bg = ACCENT if accent else CARD
        fg = "#111111" if accent else TEXT
        return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, activebackground="#E1C987" if accent else "#252540",
                         activeforeground=fg, relief="flat", padx=14, pady=10, cursor="hand2", font=("Segoe UI", 10, "bold"))

    def show_dashboard(self):
        self.clear()
        header = tk.Frame(self, bg=PANEL, height=84)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(header, bg=ACCENT, width=6).pack(side="left", fill="y")
        box = tk.Frame(header, bg=PANEL)
        box.pack(side="left", fill="both", expand=True, padx=24)
        tk.Label(box, text="M MEN STYLE — 3 TOOL LABEL SOFTWARE", fg=TEXT, bg=PANEL, font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(14,0))
        tk.Label(box, text="Single dashboard • Back navigation • Central Desktop output • Proper logo/icon", fg=MUTED, bg=PANEL, font=("Segoe UI", 10)).pack(anchor="w", pady=(3,0))
        self.button(header, "Open Output Folder", open_output_folder).pack(side="right", padx=22, pady=20)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=24)
        body.grid_columnconfigure((0,1,2), weight=1, uniform="cards")
        self.card(body, 0, "1", "Amazon Packing Slip Label Generator", "Old Amazon packing-slip/customer label tool with its premium UI. Output saved in Desktop central folder.", ["Order PDF parser", "Branch/courier settings", "Back menu included"], self.show_amazon_tool)
        self.card(body, 1, "2", "Marketplace Product Label Generator V12", "Advanced product/barcode thermal labels. Keeps your 106mm roll, 50mm label and 3mm gap settings.", ["2-up thermal labels", "CSV/Excel upload", "Central marketplace output"], self.show_marketplace_tool)
        self.card(body, 2, "3", "Flipkart / Amazon Shipping Label Cropper", "New stable cropper UI. Auto crop all pages or draw one box and apply it to every page in the full PDF.", ["100 pages supported", "Manual box applies to all", "100mm × 150mm output"], self.show_cropper)

        footer = tk.Frame(self, bg=PANEL, height=44)
        footer.pack(fill="x")
        footer.pack_propagate(False)
        tk.Label(footer, text=f"Central output: {root_dir()}", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=18)

    def card(self, parent, col, num, title, desc, points, cmd):
        outer = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        outer.grid(row=0, column=col, sticky="nsew", padx=10)
        tk.Frame(outer, bg=ACCENT, height=5).pack(fill="x")
        inner = tk.Frame(outer, bg=CARD)
        inner.pack(fill="both", expand=True, padx=20, pady=20)
        tk.Label(inner, text=f"TOOL {num}", bg=ACCENT, fg="#111111", font=("Segoe UI", 9, "bold"), padx=10, pady=4).pack(anchor="w")
        tk.Label(inner, text=title, bg=CARD, fg=TEXT, font=("Segoe UI", 15, "bold"), wraplength=270, justify="left").pack(anchor="w", pady=(20,8))
        tk.Label(inner, text=desc, bg=CARD, fg=MUTED, font=("Segoe UI", 10), wraplength=270, justify="left").pack(anchor="w")
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=18)
        for p in points:
            row = tk.Frame(inner, bg=CARD); row.pack(fill="x", pady=4)
            tk.Label(row, text="✓", bg=CARD, fg=GREEN, font=("Segoe UI", 11, "bold")).pack(side="left")
            tk.Label(row, text=p, bg=CARD, fg=TEXT, font=("Segoe UI", 9), wraplength=230, justify="left").pack(side="left", padx=7)
        tk.Frame(inner, bg=CARD).pack(fill="both", expand=True)
        self.button(inner, "Open Tool", cmd, True).pack(fill="x", pady=(18,0))

    def show_error_panel(self, tool_name, exc):
        self.clear()
        self.configure(bg=BG)
        top = tk.Frame(self, bg=PANEL, height=70)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Frame(top, bg=RED, width=6).pack(side="left", fill="y")
        self.button(top, "← Back", self.show_dashboard).pack(side="left", padx=18, pady=18)
        tk.Label(top, text=f"{tool_name} could not open", bg=PANEL, fg=TEXT, font=("Segoe UI", 16, "bold")).pack(side="left", padx=10)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=28)
        tk.Label(body, text="The app did not freeze. I am showing the exact error here so it can be fixed.", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w")
        txt = tk.Text(body, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Consolas", 9), wrap="word")
        txt.pack(fill="both", expand=True, pady=14)
        txt.insert("end", str(exc) + "\n\n" + traceback.format_exc())
        txt.config(state="disabled")

    def show_amazon_tool(self):
        self.clear()
        self.title("Amazon Packing Slip Label Generator - M Men Style")
        apply_icon(self)
        try:
            from app.gui import LabelApp
            frame = LabelApp(self, embedded=True, on_back=self.show_dashboard)
            frame.pack(fill="both", expand=True)
        except Exception as e:
            self.show_error_panel("Amazon Packing Slip Label Generator", e)

    def show_marketplace_tool(self):
        self.clear()
        self.title("Marketplace Product Label Generator V12 - M Men Style")
        apply_icon(self)
        try:
            from marketplace_v12.app import App
            frame = App(self, embedded=True, on_back=self.show_dashboard)
            frame.pack(fill="both", expand=True)
        except Exception as e:
            self.show_error_panel("Marketplace Product Label Generator V12", e)

    def show_cropper(self):
        self.clear()
        self.title("Flipkart / Amazon Shipping Label Cropper - M Men Style")
        apply_icon(self)
        try:
            from tools.flipkart_cropper.cropper_gui import LabelCropperFrame
            LabelCropperFrame(self, on_back=self.show_dashboard).pack(fill="both", expand=True)
        except Exception as e:
            self.show_error_panel("Flipkart / Amazon Shipping Label Cropper", e)


def main():
    set_windows_app_id()
    try:
        # direct modes still supported for debugging
        if "--amazon" in sys.argv:
            from app.gui import LabelApp
            app=LabelApp(); apply_icon(app.root_window); app.root_window.mainloop(); return
        if "--marketplace" in sys.argv:
            from marketplace_v12.app import App
            app=App(); apply_icon(app.root_window); app.root_window.mainloop(); return
        if "--cropper" in sys.argv:
            from tools.flipkart_cropper.cropper_gui import LabelCropperWindow
            app=LabelCropperWindow(); app.mainloop(); return
        app = Dashboard(); app.mainloop()
    except Exception as e:
        traceback.print_exc()
        try: messagebox.showerror("Application Error", f"Error occurred:\n\n{e}")
        except Exception: input("Press Enter to close...")

if __name__ == "__main__":
    main()
