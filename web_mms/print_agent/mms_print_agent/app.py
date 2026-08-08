import argparse
import logging
import platform
import socket
import time

from . import __version__
from .api_client import ApiClient
from .config import AgentSettings
from .diagnostics import create_bundle
from .spooler import WindowsRawSpooler
from .token_store import TokenStore
from .worker import PrintWorker

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="MMS Windows local RAW print agent")
    parser.add_argument("--pair"); parser.add_argument("--diagnostics", action="store_true"); args = parser.parse_args()
    settings = AgentSettings(); logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(message)s")
    store = TokenStore(settings.config_dir); token = store.load(); machine = socket.gethostname()
    if args.pair:
        result = ApiClient(settings.server_url).pair({"code": args.pair, "machine_name": machine, "name": settings.agent_name, "version": __version__})
        store.save(result["token"]); print("Paired successfully. Token stored with Windows user protection."); return
    if not token: raise SystemExit("Agent is not paired. Run with --pair CODE.")
    api = ApiClient(settings.server_url, token); spooler = WindowsRawSpooler(); printers = spooler.discover()
    if args.diagnostics: print(create_bundle(settings.config_dir, printers)); return
    api.sync_printers(printers); worker = PrintWorker(api, spooler, transport_allowed=settings.real_transport_allowed)
    last_heartbeat = 0.0; server_transport_enabled = False
    while True:
        try:
            if time.monotonic() - last_heartbeat >= settings.heartbeat_seconds:
                heartbeat=api.heartbeat({"version": __version__, "windows_version": platform.platform(), "uptime_seconds": int(time.monotonic())});server_transport_enabled=bool(heartbeat.get("transport_enabled"));last_heartbeat=time.monotonic()
            claim = api.claim() if server_transport_enabled and settings.real_transport_allowed else None
            if claim: worker.process(claim)
        except Exception: logger.exception("Agent poll failed")
        time.sleep(settings.poll_seconds)
