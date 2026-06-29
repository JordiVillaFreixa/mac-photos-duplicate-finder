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


def readable_media_roots(library: Path, scan_all_media: bool = False) -> list[Path]:
    roots = original_media_roots(library, scan_all_media=scan_all_media)
    if not roots:
        raise RuntimeError(
            f"No readable media roots found in {library}. Expected `originals` or `Masters`. "
            "If this is your Photos library, grant Full Disk Access to the terminal app you are "
            "using, then rerun the script."
        )

    unreadable: list[str] = []
    for root in roots:
        try:
            next(root.iterdir(), None)
        except (OSError, PermissionError) as exc:
            unreadable.append(f"{root}: {exc}")

    if unreadable:
        details = "; ".join(unreadable)
        raise RuntimeError(
            "Cannot read Photos library media folders. Grant Full Disk Access to the terminal app "
            f"you are using, then rerun the script. Details: {details}"
        )
    return roots
