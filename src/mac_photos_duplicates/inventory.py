from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .media_types import media_kind
from .paths import original_media_roots


@dataclass
class LibraryInventory:
    path: str
    exists: bool
    is_photos_library: bool
    can_read_package: bool
    can_read_originals: bool
    package_size_bytes: int
    total_files: int
    original_media_files: int
    original_photos: int
    original_videos: int
    has_photos_sqlite: bool
    errors: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def inventory_library(library_path: Path) -> LibraryInventory:
    library = library_path.expanduser()
    errors: list[str] = []
    exists = library.exists()
    is_photos_library = library.suffix == ".photoslibrary"
    can_read_package = False
    can_read_originals = False
    package_size_bytes = 0
    total_files = 0
    original_media_files = 0
    original_photos = 0
    original_videos = 0
    has_photos_sqlite = False

    if not exists:
        errors.append("Path does not exist.")
        return LibraryInventory(
            path=str(library),
            exists=exists,
            is_photos_library=is_photos_library,
            can_read_package=can_read_package,
            can_read_originals=can_read_originals,
            package_size_bytes=package_size_bytes,
            total_files=total_files,
            original_media_files=original_media_files,
            original_photos=original_photos,
            original_videos=original_videos,
            has_photos_sqlite=has_photos_sqlite,
            errors=errors,
        )

    try:
        next(library.iterdir(), None)
        can_read_package = True
    except (OSError, PermissionError) as exc:
        errors.append(f"Cannot list package contents: {exc}")

    has_photos_sqlite = (library / "database" / "Photos.sqlite").exists() or (
        library / "Photos.sqlite"
    ).exists()

    if can_read_package:
        for root_string, _, files in os.walk(library, onerror=lambda exc: errors.append(str(exc))):
            root = Path(root_string)
            for name in files:
                file_path = root / name
                total_files += 1
                try:
                    package_size_bytes += file_path.stat().st_size
                except (OSError, PermissionError) as exc:
                    errors.append(f"Cannot stat {file_path}: {exc}")

    roots = original_media_roots(library)
    can_read_originals = bool(roots)
    for root in roots:
        try:
            for file_path in root.rglob("*"):
                if not file_path.is_file():
                    continue
                kind = media_kind(file_path)
                if kind is None:
                    continue
                original_media_files += 1
                if kind == "photo":
                    original_photos += 1
                elif kind == "video":
                    original_videos += 1
        except (OSError, PermissionError) as exc:
            can_read_originals = False
            errors.append(f"Cannot scan originals root {root}: {exc}")

    return LibraryInventory(
        path=str(library),
        exists=exists,
        is_photos_library=is_photos_library,
        can_read_package=can_read_package,
        can_read_originals=can_read_originals,
        package_size_bytes=package_size_bytes,
        total_files=total_files,
        original_media_files=original_media_files,
        original_photos=original_photos,
        original_videos=original_videos,
        has_photos_sqlite=has_photos_sqlite,
        errors=errors,
    )
