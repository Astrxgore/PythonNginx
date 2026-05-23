"""Small LRU cache for opened static files."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import time


@dataclass(slots=True)
class OpenFileCacheEntry:
    path: Path
    fd: int
    size: int
    mtime_ns: int
    last_used: float


class OpenFileCache:
    def __init__(self, max_entries: int = 128, inactive: float = 30.0) -> None:
        self.max_entries = max_entries
        self.inactive = inactive
        self._entries: dict[Path, OpenFileCacheEntry] = {}

    def get(self, path: Path) -> OpenFileCacheEntry | None:
        path = path.resolve()
        entry = self._entries.get(path)
        if entry is None:
            return None

        try:
            stat_result = path.stat()
        except OSError:
            self._close_entry(path)
            return None

        if stat_result.st_size != entry.size or stat_result.st_mtime_ns != entry.mtime_ns:
            self._close_entry(path)
            return None

        entry.last_used = time.monotonic()
        return entry

    def open_file(self, path: Path) -> OpenFileCacheEntry:
        path = path.resolve()
        self.sweep()
        cached = self.get(path)
        if cached is not None:
            return cached

        stat_result = path.stat()
        if len(self._entries) >= self.max_entries:
            self._evict_oldest()

        fd = os.open(path, os.O_RDONLY)
        entry = OpenFileCacheEntry(
            path=path,
            fd=fd,
            size=stat_result.st_size,
            mtime_ns=stat_result.st_mtime_ns,
            last_used=time.monotonic(),
        )
        self._entries[entry.path] = entry
        return entry

    def read(self, entry: OpenFileCacheEntry) -> bytes:
        return os.pread(entry.fd, entry.size, 0)

    def sweep(self) -> None:
        now = time.monotonic()
        for path, entry in list(self._entries.items()):
            if now - entry.last_used > self.inactive:
                self._close_entry(path)

    def close_all(self) -> None:
        for path in list(self._entries):
            self._close_entry(path)

    def _evict_oldest(self) -> None:
        if not self._entries:
            return
        oldest = min(self._entries.values(), key=lambda entry: entry.last_used)
        self._close_entry(oldest.path)

    def _close_entry(self, path: Path) -> None:
        entry = self._entries.pop(path, None)
        if entry is None:
            return
        try:
            os.close(entry.fd)
        except OSError:
            pass

    def __del__(self) -> None:
        self.close_all()
