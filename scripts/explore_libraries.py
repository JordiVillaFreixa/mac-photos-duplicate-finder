#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mac_photos_duplicates.inventory import inventory_library
from mac_photos_duplicates.paths import default_search_dirs, find_photos_libraries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely inventory macOS Photos libraries without modifying them."
    )
    parser.add_argument(
        "--library",
        action="append",
        type=Path,
        help="Specific .photoslibrary path to inspect. Can be repeated.",
    )
    parser.add_argument(
        "--search-dir",
        action="append",
        type=Path,
        help="Directory to search recursively for .photoslibrary packages. Can be repeated.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/libraries.json"),
        help="JSON report path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    libraries = args.library or find_photos_libraries(args.search_dir or default_search_dirs())
    report = [inventory_library(path).to_dict() for path in libraries]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote {len(report)} library inventories to {args.output}")
    for item in report:
        access = "readable" if item["can_read_package"] else "not-readable"
        print(
            f"- {item['path']} | {access} | originals={item['original_media_files']} "
            f"photos={item['original_photos']} videos={item['original_videos']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

