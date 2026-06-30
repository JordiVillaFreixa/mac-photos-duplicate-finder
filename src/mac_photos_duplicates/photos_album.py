from __future__ import annotations

import csv
import json
import sqlite3
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from urllib.parse import quote


@dataclass
class AlbumAsset:
    path: str
    relative_path: str
    uuid: str
    cloud_asset_guid: str
    directory: str
    filename: str


@dataclass
class AlbumPlan:
    album_name: str
    id_source: str
    requested_paths: list[str]
    mapped_assets: list[AlbumAsset]
    unmapped_paths: list[str]
    duplicate_ids: list[str]


def photos_database_path(library: Path) -> Path:
    candidates = [
        library / "database" / "Photos.sqlite",
        library / "Photos.sqlite",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError(f"Photos.sqlite not found in {library}")


def proposal_paths(csv_path: Path, include_kept: bool = False) -> list[Path]:
    paths: list[Path] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if "duplicate_candidate_path" in row:
                if include_kept and row.get("keep_path"):
                    paths.append(Path(row["keep_path"]))
                if row.get("duplicate_candidate_path"):
                    paths.append(Path(row["duplicate_candidate_path"]))
            elif "first_path" in row and "second_path" in row:
                if row.get("first_path"):
                    paths.append(Path(row["first_path"]))
                if row.get("second_path"):
                    paths.append(Path(row["second_path"]))
            else:
                raise RuntimeError(
                    "Unsupported proposal CSV. Expected exact duplicate columns "
                    "`duplicate_candidate_path`/`keep_path` or probable duplicate columns "
                    "`first_path`/`second_path`."
                )
    return _dedupe_paths(paths)


def build_album_plan(
    library: Path,
    proposal_csv: Path,
    album_name: str,
    id_source: str = "uuid",
    include_kept: bool = False,
) -> AlbumPlan:
    if id_source not in {"uuid", "cloud_asset_guid"}:
        raise ValueError("id_source must be `uuid` or `cloud_asset_guid`.")

    library = library.expanduser().resolve()
    requested = proposal_paths(proposal_csv, include_kept=include_kept)
    db_path = photos_database_path(library)
    asset_index = _load_asset_index(db_path)

    mapped: list[AlbumAsset] = []
    unmapped: list[str] = []
    for path in requested:
        keys = _asset_keys_for_path(library, path)
        asset = next((asset_index[key] for key in keys if key in asset_index), None)
        if asset is None:
            unmapped.append(str(path))
            continue
        mapped.append(
            replace(
                asset,
                path=str(path),
                relative_path=str(path.expanduser().resolve().relative_to(library)),
            )
        )

    ids: list[str] = []
    duplicate_ids: list[str] = []
    seen_ids: set[str] = set()
    deduped_mapped: list[AlbumAsset] = []
    for asset in mapped:
        asset_id = asset.uuid if id_source == "uuid" else asset.cloud_asset_guid
        if not asset_id:
            unmapped.append(asset.path)
            continue
        if asset_id in seen_ids:
            duplicate_ids.append(asset_id)
            continue
        seen_ids.add(asset_id)
        ids.append(asset_id)
        deduped_mapped.append(asset)

    return AlbumPlan(
        album_name=album_name,
        id_source=id_source,
        requested_paths=[str(path) for path in requested],
        mapped_assets=deduped_mapped,
        unmapped_paths=unmapped,
        duplicate_ids=duplicate_ids,
    )


def write_album_plan(plan: AlbumPlan, output_dir: Path, batch_size: int = 100) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_path = output_dir / "photos_album_plan.json"
    plan_path.write_text(
        json.dumps(asdict(plan), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    ids_path = output_dir / "photos_album_asset_ids.txt"
    ids_path.write_text("\n".join(_asset_ids(plan)) + "\n", encoding="utf-8")

    script_path = output_dir / "create_photos_album.applescript"
    script_path.write_text(
        build_applescript(plan, ids_path=ids_path.resolve(), batch_size=batch_size),
        encoding="utf-8",
    )

    report = [
        "Photos review album plan",
        "========================",
        "",
        f"Album name: {plan.album_name}",
        f"ID source: {plan.id_source}",
        f"Requested paths: {len(plan.requested_paths)}",
        f"Mapped Photos assets: {len(plan.mapped_assets)}",
        f"Unmapped paths: {len(plan.unmapped_paths)}",
        f"Duplicate IDs skipped: {len(plan.duplicate_ids)}",
        "",
        "No Photos database was edited.",
        "No file was deleted.",
        "No file was moved inside the Photos library.",
        "",
        "The AppleScript uses Photos.app automation to create or reuse the album and add existing",
        "Photos media items by ID. Run the CLI with --execute only after reviewing this plan.",
    ]
    if plan.unmapped_paths:
        report.extend(["", "Unmapped paths:"])
        report.extend(plan.unmapped_paths)
    (output_dir / "photos_album_report.txt").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    return plan_path


def build_applescript(plan: AlbumPlan, ids_path: Path, batch_size: int = 100) -> str:
    album_literal = _applescript_string(plan.album_name)
    ids_path_literal = _applescript_string(str(ids_path))
    return f"""\
set albumName to {album_literal}
set idsPath to {ids_path_literal}
set batchSize to {batch_size}
set idsText to read POSIX file idsPath as «class utf8»
set assetIds to paragraphs of idsText

tell application "Photos"
    activate
    if exists album albumName then
        set targetAlbum to album albumName
    else
        set targetAlbum to make new album named albumName
    end if

    set addedCount to 0
    set failedItems to {{}}
    set batchItems to {{}}
    repeat with assetId in assetIds
        if (assetId as text) is "" then
            -- Skip final empty line.
        else
            try
                set itemRef to media item id (assetId as text)
                set end of batchItems to itemRef
                if (count of batchItems) is greater than or equal to batchSize then
                    add batchItems to targetAlbum
                    set addedCount to addedCount + (count of batchItems)
                    set batchItems to {{}}
                end if
            on error errMsg
                set end of failedItems to ((assetId as text) & ": " & errMsg)
            end try
        end if
    end repeat
    if (count of batchItems) is greater than 0 then
        add batchItems to targetAlbum
        set addedCount to addedCount + (count of batchItems)
    end if

    return ("added=" & addedCount & ", failed=" & (count of failedItems))
end tell
"""


def execute_applescript(
    plan: AlbumPlan,
    batch_size: int = 100,
    batch_timeout: int = 120,
    progress_callback: Callable[[str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    asset_ids = _asset_ids(plan)
    chunks = [
        asset_ids[start : start + batch_size]
        for start in range(0, len(asset_ids), batch_size)
    ]
    outputs: list[str] = []
    errors: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        if progress_callback:
            progress_callback(f"Adding batch {index}/{len(chunks)} ({len(chunk)} assets)...")
        script = _build_batch_applescript(plan.album_name, chunk)
        try:
            result = subprocess.run(
                ["osascript", "-"],
                input=script,
                text=True,
                capture_output=True,
                check=False,
                timeout=batch_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(
                args=["osascript", "-"],
                returncode=124,
                stdout="\n".join(outputs),
                stderr=(
                    "\n".join(errors)
                    + f"\nBatch {index}/{len(chunks)} timed out after {batch_timeout}s."
                ).strip(),
            )

        if result.stdout.strip():
            outputs.append(f"batch {index}/{len(chunks)}: {result.stdout.strip()}")
        if result.stderr.strip():
            errors.append(f"batch {index}/{len(chunks)}: {result.stderr.strip()}")
        if result.returncode != 0:
            return subprocess.CompletedProcess(
                args=result.args,
                returncode=result.returncode,
                stdout="\n".join(outputs),
                stderr="\n".join(errors),
            )

    return subprocess.CompletedProcess(
        args=["osascript", "-"],
        returncode=0,
        stdout="\n".join(outputs),
        stderr="\n".join(errors),
    )


def _build_batch_applescript(album_name: str, asset_ids: list[str]) -> str:
    album_literal = _applescript_string(album_name)
    list_literal = "{" + ", ".join(_applescript_string(asset_id) for asset_id in asset_ids) + "}"
    return f"""\
set albumName to {album_literal}
set assetIds to {list_literal}

tell application "Photos"
    activate
    if exists album albumName then
        set targetAlbum to album albumName
    else
        set targetAlbum to make new album named albumName
    end if

    set addedCount to 0
    set failedItems to {{}}
    set batchItems to {{}}
    repeat with assetId in assetIds
        try
            set itemRef to media item id (assetId as text)
            set end of batchItems to itemRef
        on error errMsg
            set end of failedItems to ((assetId as text) & ": " & errMsg)
        end try
    end repeat

    if (count of batchItems) is greater than 0 then
        add batchItems to targetAlbum
        set addedCount to count of batchItems
    end if

    if (count of failedItems) is greater than 0 then
        set oldDelimiters to AppleScript's text item delimiters
        set AppleScript's text item delimiters to linefeed
        set failedText to failedItems as text
        set AppleScript's text item delimiters to oldDelimiters
        return ("added=" & addedCount & ", failed=" & (count of failedItems) & linefeed & failedText)
    else
        return ("added=" & addedCount & ", failed=0")
    end if
end tell
"""


def _asset_ids(plan: AlbumPlan) -> list[str]:
    return [
        asset.uuid if plan.id_source == "uuid" else asset.cloud_asset_guid
        for asset in plan.mapped_assets
    ]


def _load_asset_index(db_path: Path) -> dict[tuple[str, str], AlbumAsset]:
    uri = f"file:{quote(str(db_path))}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    try:
        rows = connection.execute(
            """
            select ZUUID, ZCLOUDASSETGUID, ZDIRECTORY, ZFILENAME
            from ZASSET
            where ZDIRECTORY is not null
              and ZFILENAME is not null
              and ZTRASHEDSTATE = 0
            """
        ).fetchall()
    finally:
        connection.close()

    index: dict[tuple[str, str], AlbumAsset] = {}
    for uuid, cloud_guid, directory, filename in rows:
        key = (str(directory), str(filename))
        index[key] = AlbumAsset(
            path="",
            relative_path=f"originals/{directory}/{filename}",
            uuid=str(uuid or ""),
            cloud_asset_guid=str(cloud_guid or ""),
            directory=str(directory),
            filename=str(filename),
        )
        if uuid:
            index[(str(directory), str(uuid))] = index[key]
    return index


def _asset_keys_for_path(library: Path, path: Path) -> list[tuple[str, str]]:
    resolved = path.expanduser().resolve()
    relative = resolved.relative_to(library)
    parts = relative.parts
    if len(parts) < 3 or parts[0] not in {"originals", "Masters"}:
        raise RuntimeError(
            f"Cannot map path to a Photos original media item: {path}. "
            "Expected a path under originals/ or Masters/."
        )
    directory = "/".join(parts[1:-1])
    filename = parts[-1]
    keys = [(directory, filename)]
    stem = Path(filename).stem
    uuid_candidate = stem.split("_", 1)[0]
    if uuid_candidate != stem:
        keys.append((directory, uuid_candidate))
    return keys


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.expanduser())
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _applescript_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
