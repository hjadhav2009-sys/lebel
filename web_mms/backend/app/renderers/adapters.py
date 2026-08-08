from typing import Protocol


class ExternalRendererAdapter(Protocol):
    """Boundary for future BarTender, TSC SDK, and Windows GDI adapters."""
    key: str
    def render(self, snapshot: dict, profile: dict) -> bytes: ...
