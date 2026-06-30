from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote

from .photos_album import photos_database_path


@dataclass
class AssetQuality:
    path: str
    relative_path: str
    uuid: str
    width: int
    height: int
    pixel_count: int
    has_capture_date: bool
    has_location: bool
    metadata_score: int


@dataclass
class QualityDuplicateCandidate:
    path: str
    quality: AssetQuality


@dataclass
class QualityDuplicateGroup:
    sha256: str
    kind: str
    size_bytes: int
    previous_keep: str
    keep: str
    keep_quality: AssetQuality
    duplicate_candidates: list[QualityDuplicateCandidate]


def rerank_duplicate_groups_by_quality(
    library: Path,
    duplicate_groups_path: Path,
) -> list[QualityDuplicateGroup]:
    library = library.expanduser().resolve()
    raw_groups = json.loads(duplicate_groups_path.read_text(encoding="utf-8"))
    quality_index = _load_quality_index(photos_database_path(library))

    groups: list[QualityDuplicateGroup] = []
    for raw_group in raw_groups:
        paths = [raw_group["keep"], *raw_group["duplicate_candidates"]]
        ranked: list[tuple[tuple[int, int, int, int], str, AssetQuality]] = []
        for path_string in paths:
            quality = _quality_for_path(library, Path(path_string), quality_index)
            ranked.append((quality_sort_key(quality), path_string, quality))

        best_index = max(range(len(ranked)), key=lambda index: ranked[index][0])
        keep_path = ranked[best_index][1]
        keep_quality = ranked[best_index][2]
        duplicate_candidates = [
            QualityDuplicateCandidate(path=path_string, quality=quality)
            for index, (_, path_string, quality) in enumerate(ranked)
            if index != best_index
        ]
        groups.append(
            QualityDuplicateGroup(
                sha256=raw_group["sha256"],
                kind=raw_group["kind"],
                size_bytes=raw_group["size_bytes"],
                previous_keep=raw_group["keep"],
                keep=keep_path,
                keep_quality=keep_quality,
                duplicate_candidates=duplicate_candidates,
            )
        )

    return groups


def quality_sort_key(quality: AssetQuality) -> tuple[int, int, int, int]:
    return (
        quality.pixel_count,
        quality.metadata_score,
        int(quality.has_capture_date),
        int(quality.has_location),
    )


def write_quality_duplicate_reports(
    groups: list[QualityDuplicateGroup],
    output_dir: Path,
    library: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "duplicate_groups_by_quality.json").write_text(
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
                "keep_pixel_count",
                "keep_metadata_score",
                "duplicate_candidate_path",
                "duplicate_pixel_count",
                "duplicate_metadata_score",
                "duplicate_has_capture_date",
                "duplicate_has_location",
                "target_review_album",
            ],
        )
        writer.writeheader()
        for group in groups:
            for candidate in group.duplicate_candidates:
                writer.writerow(
                    {
                        "group_sha256": group.sha256,
                        "kind": group.kind,
                        "size_bytes": group.size_bytes,
                        "recommended_action": "review_lower_quality_duplicate_in_photos",
                        "keep_path": group.keep,
                        "keep_pixel_count": group.keep_quality.pixel_count,
                        "keep_metadata_score": group.keep_quality.metadata_score,
                        "duplicate_candidate_path": candidate.path,
                        "duplicate_pixel_count": candidate.quality.pixel_count,
                        "duplicate_metadata_score": candidate.quality.metadata_score,
                        "duplicate_has_capture_date": candidate.quality.has_capture_date,
                        "duplicate_has_location": candidate.quality.has_location,
                        "target_review_album": "Duplicats més baixa qualitat",
                    }
                )

    changed_keep_count = _changed_keep_count(groups)
    safety = [
        "Quality duplicate report",
        "========================",
        "",
        f"Library scanned: {library}",
        f"Duplicate groups ranked: {len(groups)}",
        f"Duplicate candidates proposed: {sum(len(group.duplicate_candidates) for group in groups)}",
        f"Groups where the quality-ranked keep differs from the old keep: {changed_keep_count}",
        "",
        "Ranking criteria, in order:",
        "1. Higher Photos pixel count: ZWIDTH * ZHEIGHT.",
        "2. Higher metadata score: capture date and real location in Photos metadata.",
        "3. Stable path order as a deterministic tie-breaker.",
        "",
        "No Photos database was edited.",
        "No file was deleted.",
        "No file was moved inside the Photos library.",
        "",
        "For exact byte duplicates, pixel and embedded file metadata are often identical. This ranking",
        "uses Photos asset metadata because duplicate files can still have different Photos records.",
    ]
    (output_dir / "quality_safety_report.txt").write_text(
        "\n".join(safety) + "\n", encoding="utf-8"
    )


def _changed_keep_count(groups: list[QualityDuplicateGroup]) -> int:
    return sum(1 for group in groups if group.keep != group.previous_keep)


def _load_quality_index(db_path: Path) -> dict[tuple[str, str], AssetQuality]:
    uri = f"file:{quote(str(db_path))}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    try:
        rows = connection.execute(
            """
            select ZUUID, ZDIRECTORY, ZFILENAME, ZWIDTH, ZHEIGHT,
                   ZDATECREATED, ZLATITUDE, ZLONGITUDE
            from ZASSET
            where ZDIRECTORY is not null
              and ZFILENAME is not null
              and ZTRASHEDSTATE = 0
            """
        ).fetchall()
    finally:
        connection.close()

    index: dict[tuple[str, str], AssetQuality] = {}
    for uuid, directory, filename, width, height, date_created, latitude, longitude in rows:
        width_int = int(width or 0)
        height_int = int(height or 0)
        has_capture_date = date_created is not None
        has_location = _has_real_location(latitude, longitude)
        quality = AssetQuality(
            path="",
            relative_path=f"originals/{directory}/{filename}",
            uuid=str(uuid or ""),
            width=width_int,
            height=height_int,
            pixel_count=width_int * height_int,
            has_capture_date=has_capture_date,
            has_location=has_location,
            metadata_score=int(has_capture_date) + int(has_location),
        )
        key = (str(directory), str(filename))
        index[key] = quality
        if uuid:
            index[(str(directory), str(uuid))] = quality
    return index


def _quality_for_path(
    library: Path,
    path: Path,
    quality_index: dict[tuple[str, str], AssetQuality],
) -> AssetQuality:
    resolved = path.expanduser().resolve()
    relative = resolved.relative_to(library)
    parts = relative.parts
    if len(parts) < 3 or parts[0] not in {"originals", "Masters"}:
        raise RuntimeError(f"Cannot map path to a Photos original media item: {path}")

    directory = "/".join(parts[1:-1])
    filename = parts[-1]
    keys = [(directory, filename)]
    stem = Path(filename).stem
    uuid_candidate = stem.split("_", 1)[0]
    if uuid_candidate != stem:
        keys.append((directory, uuid_candidate))

    quality = next((quality_index[key] for key in keys if key in quality_index), None)
    if quality is None:
        return AssetQuality(
            path=str(resolved),
            relative_path=str(relative),
            uuid="",
            width=0,
            height=0,
            pixel_count=0,
            has_capture_date=False,
            has_location=False,
            metadata_score=0,
        )

    return AssetQuality(
        path=str(resolved),
        relative_path=str(relative),
        uuid=quality.uuid,
        width=quality.width,
        height=quality.height,
        pixel_count=quality.pixel_count,
        has_capture_date=quality.has_capture_date,
        has_location=quality.has_location,
        metadata_score=quality.metadata_score,
    )


def _has_real_location(latitude: object, longitude: object) -> bool:
    if latitude is None or longitude is None:
        return False
    lat = float(latitude)
    lon = float(longitude)
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return False
    return lat != 0.0 or lon != 0.0
