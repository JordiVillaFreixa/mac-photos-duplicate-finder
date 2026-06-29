#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mac_photos_duplicates.probable import (
    find_probable_duplicate_pairs,
    require_pillow,
    write_probable_duplicate_reports,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find probable duplicate photos in a macOS Photos library."
    )
    parser.add_argument("--library", required=True, type=Path, help="Path to a .photoslibrary.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/probable-duplicates"),
        help="Directory where probable duplicate reports will be written.",
    )
    parser.add_argument(
        "--max-distance",
        type=int,
        default=6,
        help="Maximum dHash Hamming distance. Lower is stricter; 0 means visually identical hash.",
    )
    parser.add_argument(
        "--scan-all-media",
        action="store_true",
        help=(
            "Scan all photo-looking files in the package, including derivatives. "
            "Default scans only originals/Masters."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Scan only the first N matching photos. Useful for testing that the script is active.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100,
        help="Print progress every N scanned photos. Use 0 to disable progress updates.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> Path:
    library = args.library.expanduser().resolve()
    if not library.exists():
        raise SystemExit(f"Library does not exist: {library}")
    if library.suffix != ".photoslibrary":
        raise SystemExit(f"Refusing to scan a non-.photoslibrary path: {library}")
    if args.max_distance < 0:
        raise SystemExit("--max-distance must be 0 or greater.")
    if args.max_distance > 12:
        raise SystemExit(
            "Refusing --max-distance above 12 because it is likely to generate too many false positives."
        )
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be 1 or greater.")
    if args.progress_every < 0:
        raise SystemExit("--progress-every must be 0 or greater.")
    return library


def main() -> int:
    args = parse_args()
    library = validate_args(args)
    try:
        require_pillow()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Library: {library}", flush=True)
    print(
        f"Mode: {'all media in package' if args.scan_all_media else 'originals/Masters only'}",
        flush=True,
    )
    print(f"Max dHash distance: {args.max_distance}", flush=True)
    if args.limit:
        print(f"Limit: {args.limit} photos", flush=True)

    try:
        pairs, errors = find_probable_duplicate_pairs(
            library,
            max_distance=args.max_distance,
            scan_all_media=args.scan_all_media,
            limit=args.limit,
            progress_callback=lambda message: print(message, flush=True),
            progress_every=args.progress_every,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    write_probable_duplicate_reports(
        pairs,
        errors,
        args.output_dir,
        library,
        max_distance=args.max_distance,
        scan_all_media=args.scan_all_media,
    )

    print(f"Found {len(pairs)} probable duplicate pairs.")
    print(f"Skipped {len(errors)} files that could not be decoded.")
    print(f"Wrote reports to {args.output_dir}")
    print("No files were moved, copied, deleted, or edited.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
