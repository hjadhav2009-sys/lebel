import logging
from dataclasses import dataclass
from typing import Protocol


class SpoolError(RuntimeError):
    def __init__(self, message: str, *, uncertain: bool = False):
        super().__init__(message); self.uncertain = uncertain


class RawSpooler(Protocol):
    def discover(self) -> list[dict]: ...
    def spool(self, printer_name: str, data: bytes, document_name: str) -> str: ...


class WindowsRawSpooler:
    def discover(self) -> list[dict]:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        default = win32print.GetDefaultPrinter()
        result = []
        for _flags, description, name, comment in win32print.EnumPrinters(flags):
            handle = win32print.OpenPrinter(name)
            try: info = win32print.GetPrinter(handle, 2)
            finally: win32print.ClosePrinter(handle)
            port = str(info.get("pPortName") or "")
            result.append({"name": name, "driver_name": str(info.get("pDriverName") or description or "Unknown"), "port_name": port,
                "status": "online", "is_default": name == default, "is_network": port.startswith("\\\\")})
        return result

    def spool(self, printer_name: str, data: bytes, document_name: str) -> str:
        import win32print
        handle = None; job_id = None; document_started = False; page_started = False
        try:
            handle = win32print.OpenPrinter(printer_name)
            job_id = win32print.StartDocPrinter(handle, 1, (document_name, None, "RAW")); document_started = True
            win32print.StartPagePrinter(handle); page_started = True
            written = win32print.WritePrinter(handle, data)
            if written != len(data): raise SpoolError(f"Short RAW write: {written}/{len(data)}", uncertain=True)
            win32print.EndPagePrinter(handle); page_started = False
            win32print.EndDocPrinter(handle); document_started = False
            return str(job_id)
        except SpoolError: raise
        except Exception as exc: raise SpoolError(str(exc), uncertain=job_id is not None) from exc
        finally:
            if handle is not None:
                if page_started:
                    try: win32print.EndPagePrinter(handle)
                    except OSError: logging.getLogger(__name__).warning("Unable to close RAW spool page", exc_info=True)
                if document_started:
                    try: win32print.EndDocPrinter(handle)
                    except OSError: logging.getLogger(__name__).warning("Unable to close RAW spool document", exc_info=True)
                win32print.ClosePrinter(handle)


@dataclass
class FakeSpooler:
    printers: list[dict] | None = None
    fail: SpoolError | None = None

    def __post_init__(self): self.writes: list[tuple[str, bytes, str]] = []
    def discover(self) -> list[dict]: return self.printers or []
    def spool(self, printer_name: str, data: bytes, document_name: str) -> str:
        if self.fail: raise self.fail
        self.writes.append((printer_name, data, document_name)); return f"fake-{len(self.writes)}"
