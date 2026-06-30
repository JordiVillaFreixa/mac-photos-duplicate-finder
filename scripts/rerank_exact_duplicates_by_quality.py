#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mac_photos_duplicates.quality import (
    rerank_duplicate_groups_by_quality,
    write_quality_duplicate_reports,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-rank exact duplicate groups by Photos quality metadata."
    )
    parser.add_argument("--library", required=True, type=Path, help="Path to a .photoslibrary.")
    parser.add_argument(
        "--duplicate-groups",
        type=Path,
        default=Path("reports/duplicates/duplicate_groups.json"),
        help="JSON produced by find_exact_duplicates.py.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/duplicates-low-quality"),
        help="Directory where quality-ranked duplicate reports will be written.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> Path:
    library = args.library.expanduser().resolve()
    if not library.exists():
        raise SystemExit(f"Library does not exist: {library}")
    if library.suffix != ".photoslibrary":
        raise SystemExit(f"Refusing to use a non-.photoslibrary path: {library}")
    if not args.duplicate_groups.exists():
        raise SystemExit(f"Duplicate groups JSON does not exist: {args.duplicate_groups}")
    return library


def main() -> int:
    args = parse_args()
    library = validate_args(args)
    try:
        groups = rerank_duplicate_groups_by_quality(
            library=library,
            duplicate_groups_path=args.duplicate_groups,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    write_quality_duplicate_reports(groups, args.output_dir, library)
    duplicate_count = sum(len(group.duplicate_candidates) for group in groups)
    print(f"Ranked {len(groups)} exact duplicate groups by Photos quality metadata.")
    print(f"Wrote {duplicate_count} lower-quality duplicate candidates.")
    print(f"Wrote reports to {args.output_dir}")
    print("No files were moved, copied, deleted, or edited.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
