import hashlib
import os
from pathlib import Path
from typing import BinaryIO, Protocol


class PrintArtifactStore(Protocol):
    def save(self, key: str, payload: bytes) -> str: ...
    def open(self, key: str) -> BinaryIO: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...


class FileSystemPrintArtifactStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root != path and self.root not in path.parents:
            raise ValueError("INVALID_ARTIFACT_KEY")
        return path

    def save(self, key: str, payload: bytes) -> str:
        path = self._path(key); path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(payload); os.replace(temporary, path)
        return hashlib.sha256(payload).hexdigest()

    def open(self, key: str) -> BinaryIO:
        return self._path(key).open("rb")

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists(): path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()
