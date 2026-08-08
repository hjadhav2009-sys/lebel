from pathlib import Path


class TokenStore:
    def __init__(self, directory: Path):
        self.path = directory / "agent.token"

    def save(self, token: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import win32crypt
        except ImportError as exc:
            raise RuntimeError("Windows DPAPI support is required; refusing plaintext token storage.") from exc
        data = win32crypt.CryptProtectData(token.encode("utf-8"), "MMS Print Agent", None, None, None, 0)
        self.path.write_bytes(data)

    def load(self) -> str | None:
        if not self.path.exists(): return None
        try:
            import win32crypt
        except ImportError as exc:
            raise RuntimeError("Windows DPAPI support is required to read the agent token.") from exc
        data = win32crypt.CryptUnprotectData(self.path.read_bytes(), None, None, None, 0)[1]
        return data.decode("utf-8")
