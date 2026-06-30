from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mac_photos_duplicates.duplicates import find_exact_duplicate_groups
from mac_photos_duplicates.inventory import inventory_library
from mac_photos_duplicates.photos_album import build_album_plan, build_applescript
from mac_photos_duplicates.quality import rerank_duplicate_groups_by_quality
from mac_photos_duplicates.paths import readable_media_roots
from mac_photos_duplicates.probable import (
    ProbableImage,
    _find_pairs_with_bk_tree,
    format_progress,
    hamming_distance,
)


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

    def test_hamming_distance_counts_different_bits(self) -> None:
        self.assertEqual(hamming_distance(0b1010, 0b1001), 2)
        self.assertEqual(hamming_distance(0b1111, 0b1111), 0)

    def test_bk_tree_finds_probable_pairs(self) -> None:
        images = [
            ProbableImage("a.jpg", "a.jpg", 100, "0000000000000000"),
            ProbableImage("b.jpg", "b.jpg", 101, "0000000000000001"),
            ProbableImage("c.jpg", "c.jpg", 102, "ffffffffffffffff"),
        ]

        pairs = _find_pairs_with_bk_tree(images, max_distance=1)

        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0].first_path, "a.jpg")
        self.assertEqual(pairs[0].second_path, "b.jpg")

    def test_format_progress_includes_percentage(self) -> None:
        self.assertEqual(format_progress(25, 100), "25/100 photos (25.0%)")
        self.assertEqual(format_progress(5, 0), "5 photos")

    def test_readable_media_roots_fails_without_originals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp) / "Test.photoslibrary"
            library.mkdir()

            with self.assertRaises(RuntimeError) as context:
                readable_media_roots(library)

        self.assertIn("No readable media roots", str(context.exception))

    def test_build_album_plan_maps_exact_duplicate_csv_to_asset_uuid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "Test.photoslibrary"
            originals = library / "originals" / "A"
            database = library / "database"
            originals.mkdir(parents=True)
            database.mkdir()
            candidate = originals / "ASSET-1.jpeg"
            candidate.write_bytes(b"image")

            db_path = database / "Photos.sqlite"
            import sqlite3

            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "create table ZASSET ("
                    "ZUUID text, ZCLOUDASSETGUID text, ZDIRECTORY text, "
                    "ZFILENAME text, ZTRASHEDSTATE integer)"
                )
                connection.execute(
                    "insert into ZASSET values (?, ?, ?, ?, ?)",
                    ("uuid-1", "cloud-1", "A", "ASSET-1.jpeg", 0),
                )
                connection.commit()
            finally:
                connection.close()

            proposal = root / "duplicate_proposal.csv"
            proposal.write_text(
                "keep_path,duplicate_candidate_path\n"
                f"{originals / 'KEEP.jpeg'},{candidate}\n",
                encoding="utf-8",
            )

            plan = build_album_plan(library, proposal, "Duplicats candidats")

        self.assertEqual(len(plan.mapped_assets), 1)
        self.assertEqual(plan.mapped_assets[0].uuid, "uuid-1")
        self.assertEqual(plan.unmapped_paths, [])

    def test_build_album_plan_maps_live_photo_video_resource_by_uuid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "Test.photoslibrary"
            originals = library / "originals" / "A"
            database = library / "database"
            originals.mkdir(parents=True)
            database.mkdir()
            candidate = originals / "uuid-1_3.mov"
            candidate.write_bytes(b"video")

            db_path = database / "Photos.sqlite"
            import sqlite3

            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "create table ZASSET ("
                    "ZUUID text, ZCLOUDASSETGUID text, ZDIRECTORY text, "
                    "ZFILENAME text, ZTRASHEDSTATE integer)"
                )
                connection.execute(
                    "insert into ZASSET values (?, ?, ?, ?, ?)",
                    ("uuid-1", "cloud-1", "A", "uuid-1.jpeg", 0),
                )
                connection.commit()
            finally:
                connection.close()

            proposal = root / "duplicate_proposal.csv"
            proposal.write_text(
                "keep_path,duplicate_candidate_path\n"
                f"{originals / 'KEEP.jpeg'},{candidate}\n",
                encoding="utf-8",
            )

            plan = build_album_plan(library, proposal, "Duplicats candidats")

        self.assertEqual(len(plan.mapped_assets), 1)
        self.assertEqual(plan.mapped_assets[0].uuid, "uuid-1")
        self.assertEqual(plan.unmapped_paths, [])

    def test_build_applescript_reads_ids_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "Test.photoslibrary"
            originals = library / "originals" / "A"
            database = library / "database"
            originals.mkdir(parents=True)
            database.mkdir()
            candidate = originals / "ASSET-1.jpeg"
            candidate.write_bytes(b"image")

            db_path = database / "Photos.sqlite"
            import sqlite3

            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "create table ZASSET ("
                    "ZUUID text, ZCLOUDASSETGUID text, ZDIRECTORY text, "
                    "ZFILENAME text, ZTRASHEDSTATE integer)"
                )
                connection.execute(
                    "insert into ZASSET values (?, ?, ?, ?, ?)",
                    ("uuid-1", "cloud-1", "A", "ASSET-1.jpeg", 0),
                )
                connection.commit()
            finally:
                connection.close()

            proposal = root / "duplicate_proposal.csv"
            proposal.write_text(
                "keep_path,duplicate_candidate_path\n"
                f"{originals / 'KEEP.jpeg'},{candidate}\n",
                encoding="utf-8",
            )

            plan = build_album_plan(library, proposal, "Duplicats candidats")
            script = build_applescript(plan, ids_path=root / "ids.txt", batch_size=25)

        self.assertIn("set idsText to read POSIX file idsPath", script)
        self.assertIn("set assetIds to paragraphs of idsText", script)
        self.assertIn("set batchSize to 25", script)
        self.assertIn("add batchItems to targetAlbum", script)
        self.assertNotIn("set assetIds to {", script)

    def test_quality_ranking_keeps_highest_pixel_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "Test.photoslibrary"
            originals = library / "originals" / "A"
            database = library / "database"
            originals.mkdir(parents=True)
            database.mkdir()
            low = originals / "LOW.jpeg"
            high = originals / "HIGH.jpeg"
            low.write_bytes(b"same")
            high.write_bytes(b"same")

            db_path = database / "Photos.sqlite"
            import sqlite3

            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "create table ZASSET ("
                    "ZUUID text, ZDIRECTORY text, ZFILENAME text, "
                    "ZWIDTH integer, ZHEIGHT integer, ZDATECREATED real, "
                    "ZLATITUDE real, ZLONGITUDE real, ZTRASHEDSTATE integer)"
                )
                connection.execute(
                    "insert into ZASSET values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ("low-uuid", "A", "LOW.jpeg", 100, 100, 1.0, -180.0, -180.0, 0),
                )
                connection.execute(
                    "insert into ZASSET values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ("high-uuid", "A", "HIGH.jpeg", 200, 200, 1.0, -180.0, -180.0, 0),
                )
                connection.commit()
            finally:
                connection.close()

            groups_json = root / "duplicate_groups.json"
            groups_json.write_text(
                "[{"
                '"sha256":"abc",'
                '"size_bytes":4,'
                '"kind":"photo",'
                f'"keep":"{low}",'
                f'"duplicate_candidates":["{high}"]'
                "}]",
                encoding="utf-8",
            )

            groups = rerank_duplicate_groups_by_quality(library, groups_json)

        self.assertEqual(groups[0].keep, str(high))
        self.assertEqual(groups[0].previous_keep, str(low))
        self.assertEqual(groups[0].duplicate_candidates[0].path, str(low))


if __name__ == "__main__":
    unittest.main()
