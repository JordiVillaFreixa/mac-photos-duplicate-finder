from __future__ import annotations

import csv
import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from .media_types import media_kind
from .paths import readable_media_roots


@dataclass
class MediaFile:
    path: str
    relative_path: str
    size_bytes: int
    sha256: str
    kind: str


@dataclass
class DuplicateGroup:
    sha256: str
    size_bytes: int
    kind: str
    keep: str
    duplicate_candidates: list[str]


def iter_media_files(library: Path, scan_all_media: bool = False) -> list[Path]:
    roots = readable_media_roots(library, scan_all_media=scan_all_media)
    media_files: list[Path] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and media_kind(path) is not None:
                media_files.append(path)
    return sorted(media_files)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def find_exact_duplicate_groups(
    library_path: Path,
    scan_all_media: bool = False,
) -> list[DuplicateGroup]:
    library = library_path.expanduser().resolve()
    files = iter_media_files(library, scan_all_media=scan_all_media)

    by_size: dict[int, list[Path]] = {}
    for path in files:
        try:
            by_size.setdefault(path.stat().st_size, []).append(path)
        except (OSError, PermissionError):
            continue

    hashed: dict[tuple[int, str, str], list[MediaFile]] = {}
    for size, same_size_paths in by_size.items():
        if len(same_size_paths) < 2:
            continue
        for path in same_size_paths:
            kind = media_kind(path)
            if kind is None:
                continue
            digest = sha256_file(path)
            relative_path = str(path.relative_to(library))
            media_file = MediaFile(
                path=str(path),
                relative_path=relative_path,
                size_bytes=size,
                sha256=digest,
                kind=kind,
            )
            hashed.setdefault((size, digest, kind), []).append(media_file)

    groups: list[DuplicateGroup] = []
    for (size, digest, kind), entries in hashed.items():
        if len(entries) < 2:
            continue
        ordered = sorted(entries, key=lambda item: item.relative_path)
        groups.append(
            DuplicateGroup(
                sha256=digest,
                size_bytes=size,
                kind=kind,
                keep=ordered[0].path,
                duplicate_candidates=[entry.path for entry in ordered[1:]],
            )
        )

    return sorted(groups, key=lambda group: (group.kind, group.size_bytes, group.sha256))


def write_duplicate_reports(
    groups: list[DuplicateGroup],
    output_dir: Path,
    library: Path,
    scan_all_media: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "duplicate_groups.json"
    json_path.write_text(
        json.dumps([asdict(group) for group in groups], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    csv_path = output_dir / "duplicate_proposal.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "group_sha256",
                "kind",
                "size_bytes",
                "recommended_action",
                "keep_path",
                "duplicate_candidate_path",
                "target_review_album",
            ],
        )
        writer.writeheader()
        for group in groups:
            for duplicate_path in group.duplicate_candidates:
                writer.writerow(
                    {
                        "group_sha256": group.sha256,
                        "kind": group.kind,
                        "size_bytes": group.size_bytes,
                        "recommended_action": "review_in_photos_before_any_delete",
                        "keep_path": group.keep,
                        "duplicate_candidate_path": duplicate_path,
                        "target_review_album": "Duplicats",
                    }
                )

    safety = [
        "Safety report",
        "=============",
        "",
        f"Library scanned: {library}",
        f"Scan mode: {'all media in package' if scan_all_media else 'originals/Masters only'}",
        f"Duplicate groups found: {len(groups)}",
        "",
        "No Photos database was edited.",
        "No file was deleted.",
        "No file was moved inside the Photos library.",
        "",
        "The CSV is a proposal for manual review. Use Photos.app or supported Apple automation",
        "for any final album, folder, merge, or delete operation.",
    ]
    (output_dir / "safety_report.txt").write_text("\n".join(safety) + "\n", encoding="utf-8")


def copy_duplicate_candidates(groups: list[DuplicateGroup], destination: Path, library: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    library = library.resolve()
    for group in groups:
        for duplicate_path_string in group.duplicate_candidates:
            duplicate_path = Path(duplicate_path_string)
            relative = duplicate_path.resolve().relative_to(library)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(duplicate_path, target)
