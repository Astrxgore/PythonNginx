from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pynginx.static.open_file_cache import OpenFileCache


class OpenFileCacheTests(unittest.TestCase):
    def test_evicts_oldest_entry_when_full(self) -> None:
        with TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.txt"
            second = Path(tmp) / "second.txt"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")
            cache = OpenFileCache(max_entries=1)

            cache.open_file(first)
            cache.open_file(second)

            self.assertIsNone(cache.get(first))
            self.assertIsNotNone(cache.get(second))
            cache.close_all()
