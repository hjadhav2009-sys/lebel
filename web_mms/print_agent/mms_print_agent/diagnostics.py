import json
import platform
import zipfile
from datetime import UTC, datetime
from pathlib import Path


def create_bundle(directory: Path, printers: list[dict], error: str | None = None) -> Path:
    directory.mkdir(parents=True, exist_ok=True); target = directory / "mms-print-agent-diagnostics.zip"
    payload = {"created_at": datetime.now(UTC).isoformat(), "platform": platform.platform(), "printers": printers, "last_error": error}
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle: bundle.writestr("diagnostics.json", json.dumps(payload, indent=2))
    return target
