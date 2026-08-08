import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any, Protocol

from PIL import Image


class RendererError(ValueError):
    def __init__(self, code: str, message: str, diagnostics: dict | None = None):
        self.code, self.message, self.diagnostics = code, message, diagnostics or {}
        super().__init__(code)


@dataclass(frozen=True)
class RenderValidationResult:
    fits: bool
    errors: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RenderResult:
    raw_bytes: bytes
    content_type: str
    artifact_type: str
    renderer_key: str
    renderer_version: str
    label_count: int
    warnings: list[str]
    diagnostics: dict


@dataclass(frozen=True)
class PreviewResult:
    png_bytes: bytes
    diagnostics: dict


class LabelRenderer(Protocol):
    key: str
    version: str
    def validate(self, snapshots: list[dict], profile: dict) -> RenderValidationResult: ...
    def render(self, snapshots: list[dict], profile: dict) -> RenderResult: ...
    def preview(self, snapshots: list[dict], profile: dict) -> PreviewResult: ...


def mm_to_dots(mm: float | Decimal, dpi: int) -> int:
    return round(float(mm) * dpi / 25.4)


def format_mrp(value: Any) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise RendererError("MISSING_MRP", "A numeric snapshot MRP is required.") from exc
    if amount <= 0:
        raise RendererError("MISSING_MRP", "A positive snapshot MRP is required.")
    return f"Rs.{amount.quantize(Decimal('0.01'))} (inclusive of all Taxes)"


def validate_barcode(value: Any, *, max_length: int = 80) -> str:
    text = str(value or "").strip()
    if not text or len(text) > max_length or not re.fullmatch(r"[A-Za-z0-9._/+\-]+", text):
        raise RendererError("INVALID_BARCODE_VALUE", "Barcode is blank or contains unsupported characters.")
    try:
        text.encode("ascii", errors="strict")
    except UnicodeEncodeError as exc:
        raise RendererError("INVALID_BARCODE_VALUE", "Barcode is not ASCII encodable.") from exc
    return text


def snapshot_value(snapshot: dict, name: str, default=None):
    fields = snapshot.get("label_fields") or {}
    wanted = name.replace("_", " ").casefold()
    for key, value in fields.items():
        if str(key).replace("_", " ").casefold() == wanted:
            return value
    return snapshot.get(name, default)


def expand_copies(snapshots: list[dict]) -> list[dict]:
    expanded = []
    for snapshot in snapshots:
        count = int(snapshot.get("print_quantity") or 0)
        if count < 1:
            raise RendererError("INVALID_PRINT_QTY", "Snapshot print quantity must be positive.")
        expanded.extend([snapshot] * count)
    return expanded


def plan_two_up(snapshots: list[dict]) -> list[tuple[dict, dict | None]]:
    labels = expand_copies(snapshots)
    return [(labels[index], labels[index + 1] if index + 1 < len(labels) else None) for index in range(0, len(labels), 2)]


def png_bytes(image: Image.Image) -> bytes:
    output = BytesIO(); image.save(output, format="PNG", optimize=True); return output.getvalue()


def tspl_escape(value: Any) -> str:
    text = str(value or "")
    if any(ord(char) < 32 for char in text):
        raise RendererError("INVALID_TEXT_ENCODING", "Required text contains control characters.")
    return text.replace('"', "'")
