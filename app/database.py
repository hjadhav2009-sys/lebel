"""
database.py
Handles CSV saving, searching, loading of order records.
Also handles persistent storage of Branch Profiles and Courier list.

Two CSV files are maintained:
  orders.csv          — current session only (overwritten each run)
  orders_database.csv — permanent historical log (append-only, never deleted)

Branch profiles and couriers are stored in:
  settings.json       — persistent app settings
"""

import csv
import os
import json
from datetime import datetime


# ─── Column headers ──────────────────────────────────────────────────────────
HEADERS = [
    "Order ID", "Customer Name", "Phone", "Address", "Product",
    "SKU", "ASIN", "Quantity", "Amount", "Shipping Service",
    "Order Date", "Seller Name", "Generated Date", "Generated Time",
    "Custom Order", "Customisation", "Branch", "Brand", "Courier",
]


# ─────────────────────────────────────────────
# SETTINGS (branches + couriers)
# ─────────────────────────────────────────────

def _settings_path():
    folder = os.path.join(os.path.expanduser("~"), "Desktop", "MMS_Label_Tools_Output", "Amazon_Packing_Labels")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "settings.json")


def load_settings():
    """Load full settings dict. Returns defaults if file missing."""
    path = _settings_path()
    defaults = {
        "branches": [
            {
                "id": "branch_1",
                "branch_name": "Mumbai",
                "brand_name": "Sujal Fashion Works",
                "address": "Shop F-10, First Floor, Amarante\nPlot No.04, Sector-9E, Kalamboli - 410218\nContact: 9594790929",
                "logo_path": "",
            }
        ],
        "couriers": [
            "Maruti Courier",
            "Delhivery",
            "Ship Rocket",
            "Amazon Logistics",
            "DTDC",
            "Blue Dart",
            "Ecom Express",
        ],
        "last_branch_id": "branch_1",
        "last_courier": "Delhivery",
    }
    if not os.path.exists(path):
        save_settings(defaults)
        return defaults
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge missing keys
        for k, v in defaults.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        return defaults


def save_settings(settings):
    """Persist settings to JSON."""
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Settings Save Error] {e}")


def get_branches():
    return load_settings().get("branches", [])


def get_couriers():
    return load_settings().get("couriers", [])


def save_branch(branch_dict):
    """Add or update a branch. Identified by 'id'."""
    settings = load_settings()
    branches = settings.get("branches", [])
    for i, b in enumerate(branches):
        if b.get("id") == branch_dict.get("id"):
            branches[i] = branch_dict
            settings["branches"] = branches
            save_settings(settings)
            return
    branches.append(branch_dict)
    settings["branches"] = branches
    save_settings(settings)


def delete_branch(branch_id):
    settings = load_settings()
    settings["branches"] = [b for b in settings.get("branches", []) if b.get("id") != branch_id]
    save_settings(settings)


def save_couriers(couriers_list):
    settings = load_settings()
    settings["couriers"] = couriers_list
    save_settings(settings)


def set_last_used(branch_id=None, courier=None):
    settings = load_settings()
    if branch_id is not None:
        settings["last_branch_id"] = branch_id
    if courier is not None:
        settings["last_courier"] = courier
    save_settings(settings)


def get_last_used():
    s = load_settings()
    return s.get("last_branch_id", ""), s.get("last_courier", "")


# ─────────────────────────────────────────────
# SAVE ORDERS
# ─────────────────────────────────────────────

def save_orders_to_csv(orders, output_csv, overwrite=False):
    try:
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        mode = 'w' if overwrite else 'a'
        file_exists = os.path.isfile(output_csv)
        write_header = overwrite or not file_exists
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        with open(output_csv, mode=mode, newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(HEADERS)
            for order in orders:
                try:
                    writer.writerow([
                        order.get('order_id', ''),
                        order.get('ship_name', ''),
                        order.get('ship_phone', ''),
                        order.get('ship_address', ''),
                        order.get('product_name', ''),
                        order.get('sku', ''),
                        order.get('asin', ''),
                        order.get('qty', '1'),
                        order.get('grand_total', ''),
                        order.get('shipping_service', ''),
                        order.get('order_date', ''),
                        order.get('seller_name', ''),
                        date_str,
                        time_str,
                        "Yes" if order.get('is_custom') else "No",
                        " | ".join(order.get('customisations', [])),
                        order.get('branch_name', ''),
                        order.get('brand_name', ''),
                        order.get('courier', ''),
                    ])
                except Exception as e:
                    print(f"[DB Row Error] {e}")
    except Exception as e:
        print(f"[DB Save Error] {e}")


def load_all_orders(csv_path):
    data = []
    if not os.path.exists(csv_path):
        return data
    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            data = list(reader)
    except Exception as e:
        print(f"[DB Load Error] {e}")
    return data


def search_orders(csv_path, keyword):
    results = []
    kw = keyword.lower()
    for row in load_all_orders(csv_path):
        if (
            kw in row.get("Customer Name", "").lower()
            or kw in row.get("Phone", "").lower()
            or kw in row.get("Order ID", "").lower()
            or kw in row.get("Product", "").lower()
        ):
            results.append(row)
    return results