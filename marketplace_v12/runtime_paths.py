import json
import os
import shutil
import sys
from pathlib import Path


APPDATA_FOLDER = "MMS_Label_Tools"
DEFAULT_OUTPUT_FOLDER = "MMS_Label_Tools_Output"
AMAZON_TEMPLATE_RELATIVE = Path("reference_templates") / "amazon" / "amazon_template.prn"


def desktop_dir():
    desktop = Path.home() / "Desktop"
    return desktop if desktop.exists() else Path.home()


def appdata_root():
    bases = [
        os.environ.get("APPDATA"),
        os.environ.get("LOCALAPPDATA"),
        os.environ.get("TEMP"),
        os.environ.get("TMP"),
    ]
    bases.append(str(Path.cwd()))
    for base in bases:
        if not base:
            continue
        root = Path(base) / APPDATA_FOLDER
        try:
            root.mkdir(parents=True, exist_ok=True)
            return root
        except Exception:
            continue
    return Path.cwd() / APPDATA_FOLDER


def resources_dir():
    return appdata_root() / "resources"


def settings_dir():
    return appdata_root() / "settings"


def templates_dir():
    return appdata_root() / "templates"


def amazon_template_dir():
    return templates_dir() / "amazon"


def app_settings_path():
    return settings_dir() / "app_settings.json"


def amazon_template_path():
    return amazon_template_dir() / "amazon_template.prn"


def _read_json(path, default):
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return dict(default)


def load_app_settings():
    return _read_json(app_settings_path(), {"output_root": str(default_output_root())})


def save_app_settings(data):
    settings_dir().mkdir(parents=True, exist_ok=True)
    clean = load_app_settings()
    if data.get("output_root"):
        clean["output_root"] = str(Path(str(data["output_root"])).expanduser())
    app_settings_path().write_text(json.dumps(clean, indent=2), encoding="utf-8")
    ensure_output_folders(Path(clean["output_root"]))
    return clean


def default_output_root():
    return desktop_dir() / DEFAULT_OUTPUT_FOLDER


def output_root():
    settings = load_app_settings()
    root = Path(str(settings.get("output_root") or default_output_root())).expanduser()
    try:
        ensure_output_folders(root)
        return root
    except PermissionError:
        fallback = appdata_root() / "outputs"
        ensure_output_folders(fallback)
        return fallback


def ensure_output_folders(root=None):
    root = Path(root or default_output_root()).expanduser()
    for sub in [
        "",
        "Marketplace_Product_Labels",
        "Marketplace_Product_Labels/Amazon",
        "Marketplace_Product_Labels/Flipkart",
        "Marketplace_Product_PRN",
        "Amazon_Packing_Labels",
        "Flipkart_Amazon_Cropped_Labels",
        "Reports",
        "Logs",
        "Database",
        "Database/amazon_packing",
        "Database/marketplace_v12",
        "Database/output_records",
        "Raw_Uploads",
        "Raw_Uploads/Amazon_Packing_Labels",
        "Raw_Uploads/Marketplace_Product_Labels",
        "Raw_Uploads/Flipkart_Amazon_Cropped_Labels",
        "Temp",
    ]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def amazon_output_dir():
    path = output_root() / "Marketplace_Product_Labels" / "Amazon"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir():
    path = output_root() / "Logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_resource_path(relative_path):
    relative = Path(relative_path)
    candidates = []
    bundle_root = getattr(sys, "_MEIPASS", "")
    if bundle_root:
        candidates.append(Path(bundle_root) / relative)
        candidates.append(Path(bundle_root) / "marketplace_v12" / relative)
    if getattr(sys, "frozen", False):
        exe_root = Path(sys.executable).resolve().parent
        candidates.append(exe_root / relative)
        candidates.append(exe_root / "marketplace_v12" / relative)
    source_root = Path(__file__).resolve().parent
    candidates.append(source_root / relative)
    candidates.append(resources_dir() / relative)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else source_root / relative


def _bundled_amazon_template_source():
    candidates = []
    bundle_root = getattr(sys, "_MEIPASS", "")
    if bundle_root:
        candidates.extend(
            [
                Path(bundle_root) / AMAZON_TEMPLATE_RELATIVE,
                Path(bundle_root) / "marketplace_v12" / AMAZON_TEMPLATE_RELATIVE,
            ]
        )
    if getattr(sys, "frozen", False):
        exe_root = Path(sys.executable).resolve().parent
        candidates.extend(
            [
                exe_root / AMAZON_TEMPLATE_RELATIVE,
                exe_root / "marketplace_v12" / AMAZON_TEMPLATE_RELATIVE,
            ]
        )
    source_root = Path(__file__).resolve().parent
    candidates.append(source_root / AMAZON_TEMPLATE_RELATIVE)
    candidates.append(resources_dir() / AMAZON_TEMPLATE_RELATIVE)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def ensure_default_resources_installed():
    root = appdata_root()
    resources_dir().mkdir(parents=True, exist_ok=True)
    settings_dir().mkdir(parents=True, exist_ok=True)
    amazon_template_dir().mkdir(parents=True, exist_ok=True)
    ensure_output_folders(output_root())

    installed_template = amazon_template_path()
    if not installed_template.exists():
        source = _bundled_amazon_template_source()
        if source and source.exists():
            shutil.copyfile(source, installed_template)
    return {
        "appdata_root": root,
        "amazon_template": installed_template,
        "output_root": output_root(),
    }
