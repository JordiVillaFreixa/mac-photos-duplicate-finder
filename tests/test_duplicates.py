from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mac_photos_duplicates.duplicates import find_exact_duplicate_groups
from mac_photos_duplicates.inventory import inventory_library


class DuplicateDetectionTests(unittest.TestCase):
    def test_finds_exact_duplicates_under_originals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp) / "Test.photoslibrary"
            originals = library / "originals" / "0"
            originals.mkdir(parents=True)
            (originals / "a.jpg").write_bytes(b"same image bytes")
            (originals / "b.jpg").write_bytes(b"same image bytes")
            (originals / "c.jpg").write_bytes(b"different bytes")

            groups = find_exact_duplicate_groups(library)

        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].duplicate_candidates), 1)
        self.assertTrue(groups[0].keep.endswith("a.jpg"))

    def test_inventory_counts_original_media(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp) / "Test.photoslibrary"
            originals = library / "originals" / "0"
            database = library / "database"
            originals.mkdir(parents=True)
            database.mkdir()
            (database / "Photos.sqlite").write_bytes(b"not read by inventory")
            (originals / "a.heic").write_bytes(b"a")
            (originals / "b.mov").write_bytes(b"b")
            (originals / "notes.txt").write_text("ignore", encoding="utf-8")

            result = inventory_library(library)

        self.assertTrue(result.can_read_package)
        self.assertTrue(result.has_photos_sqlite)
        self.assertEqual(result.original_media_files, 2)
        self.assertEqual(result.original_photos, 1)
        self.assertEqual(result.original_videos, 1)


if __name__ == "__main__":
    unittest.main()
