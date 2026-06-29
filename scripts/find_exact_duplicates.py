#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mac_photos_duplicates.duplicates import (
    copy_duplicate_candidates,
    find_exact_duplicate_groups,
    write_duplicate_reports,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find exact duplicate original media in a macOS Photos library."
    )
    parser.add_argument("--library", required=True, type=Path, help="Path to a .photoslibrary.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/duplicates"),
        help="Directory where duplicate reports will be written.",
    )
    parser.add_argument(
        "--scan-all-media",
        action="store_true",
        help=(
            "Scan all media-looking files in the package, including derivatives. "
            "Default scans only originals/Masters."
        ),
    )
    parser.add_argument(
        "--copy-candidates-to",
        type=Path,
        help="Optional external folder for review copies of duplicate candidates. Never use a path inside the Photos library.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    library = args.library.expanduser().resolve()
    if not library.exists():
        raise SystemExit(f"Library does not exist: {library}")
    if library.suffix != ".photoslibrary":
        raise SystemExit(f"Refusing to scan a non-.photoslibrary path: {library}")
    if args.copy_candidates_to:
        destination = args.copy_candidates_to.expanduser().resolve()
        try:
            destination.relative_to(library)
        except ValueError:
            return
        raise SystemExit(
            "Refusing to copy duplicate candidates into the Photos library package. "
            "Choose an external review folder."
        )


def main() -> int:
    args = parse_args()
    validate_args(args)

    library = args.library.expanduser().resolve()
    try:
        groups = find_exact_duplicate_groups(library, scan_all_media=args.scan_all_media)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    write_duplicate_reports(groups, args.output_dir, library, scan_all_media=args.scan_all_media)

    if args.copy_candidates_to:
        copy_duplicate_candidates(groups, args.copy_candidates_to.expanduser().resolve(), library)

    duplicate_count = sum(len(group.duplicate_candidates) for group in groups)
    print(f"Found {len(groups)} exact duplicate groups with {duplicate_count} duplicate candidates.")
    print(f"Wrote reports to {args.output_dir}")
    if args.copy_candidates_to:
        print(f"Copied review candidates to {args.copy_candidates_to}")
    else:
        print("No files were moved, copied, deleted, or edited.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
