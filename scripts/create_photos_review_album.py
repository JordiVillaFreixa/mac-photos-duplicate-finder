#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mac_photos_duplicates.photos_album import (
    build_album_plan,
    execute_applescript,
    write_album_plan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a safe Photos review album from duplicate proposal CSV files."
    )
    parser.add_argument("--library", required=True, type=Path, help="Path to a .photoslibrary.")
    parser.add_argument(
        "--proposal-csv",
        required=True,
        type=Path,
        help=(
            "CSV produced by find_exact_duplicates.py or find_probable_duplicates.py. "
            "Exact CSVs add duplicate candidates; probable CSVs add both items in each pair."
        ),
    )
    parser.add_argument(
        "--album-name",
        default="Duplicats candidats",
        help="Photos album to create or reuse for manual review.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/photos-album"),
        help="Directory where the plan, report, and AppleScript will be written.",
    )
    parser.add_argument(
        "--id-source",
        choices=("uuid", "cloud_asset_guid"),
        default="uuid",
        help="Photos asset ID column to use in AppleScript.",
    )
    parser.add_argument(
        "--include-kept",
        action="store_true",
        help="For exact duplicate CSVs, include the recommended keep files too.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually run Photos.app automation. Without this, only a review plan is written.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of Photos items to add per AppleScript add call.",
    )
    parser.add_argument(
        "--batch-timeout",
        type=int,
        default=120,
        help="Maximum seconds to wait for each AppleScript batch.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> Path:
    library = args.library.expanduser().resolve()
    if not library.exists():
        raise SystemExit(f"Library does not exist: {library}")
    if library.suffix != ".photoslibrary":
        raise SystemExit(f"Refusing to use a non-.photoslibrary path: {library}")
    proposal_csv = args.proposal_csv.expanduser().resolve()
    if not proposal_csv.exists():
        raise SystemExit(f"Proposal CSV does not exist: {proposal_csv}")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be 1 or greater.")
    if args.batch_timeout < 1:
        raise SystemExit("--batch-timeout must be 1 or greater.")
    return library


def main() -> int:
    args = parse_args()
    library = validate_args(args)
    proposal_csv = args.proposal_csv.expanduser().resolve()

    try:
        plan = build_album_plan(
            library=library,
            proposal_csv=proposal_csv,
            album_name=args.album_name,
            id_source=args.id_source,
            include_kept=args.include_kept,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    write_album_plan(plan, args.output_dir, batch_size=args.batch_size)

    print(f"Requested paths: {len(plan.requested_paths)}")
    print(f"Mapped Photos assets: {len(plan.mapped_assets)}")
    print(f"Unmapped paths: {len(plan.unmapped_paths)}")
    print(f"Wrote review plan to {args.output_dir}")

    if not args.execute:
        print("Dry run only. Rerun with --execute to create/update the Photos album.")
        return 0

    if plan.unmapped_paths:
        raise SystemExit(
            "Refusing to execute because some paths could not be mapped. "
            "Review photos_album_report.txt first."
        )

    result = execute_applescript(
        plan,
        batch_size=args.batch_size,
        batch_timeout=args.batch_timeout,
        progress_callback=lambda message: print(message, flush=True),
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
