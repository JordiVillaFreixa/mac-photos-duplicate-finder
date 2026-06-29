from __future__ import annotations

from pathlib import Path


def default_search_dirs() -> list[Path]:
    home = Path.home()
    candidates = [
        home / "Pictures",
        Path("/Volumes"),
    ]
    return [path for path in candidates if path.exists()]


def find_photos_libraries(search_dirs: list[Path]) -> list[Path]:
    libraries: list[Path] = []
    seen: set[Path] = set()
    for search_dir in search_dirs:
        try:
            iterator = search_dir.rglob("*.photoslibrary")
            for path in iterator:
                resolved = path.expanduser().resolve()
                if resolved not in seen:
                    libraries.append(resolved)
                    seen.add(resolved)
        except (OSError, PermissionError):
            continue
    return sorted(libraries)


def original_media_roots(library: Path, scan_all_media: bool = False) -> list[Path]:
    if scan_all_media:
        return [library]

    roots = []
    for name in ("originals", "Masters"):
        path = library / name
        if path.exists():
            roots.append(path)
    return roots

