"""LRU cache for opened static files.

Implement after the basic static server works. Keep the API small:

- get(path) -> cached entry or None
- put(path, file object, stat)
- sweep() to close inactive entries
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class OpenFileCacheEntry:
    path: Path
    size: int
    mtime_ns: int
    last_used: float
    data: bytes


class OpenFileCache:
    def __init__(self, max_entries: int = 128, inactive: float = 30.0) -> None:
        self.max_entries = max_entries
        self.inactive = inactive
        self._entries: dict[Path, OpenFileCacheEntry] = {}

    def get(self, path: Path) -> OpenFileCacheEntry | None:
        return self._entries.get(path)

    def put(self, entry: OpenFileCacheEntry) -> None:
        self._entries[entry.path] = entry
