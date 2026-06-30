from __future__ import annotations

from pathlib import Path


FULL_DISK_ACCESS_HELP = """\
Cannot read the media files inside this Photos library.

macOS is probably blocking access to the Photos library package. Grant Full Disk Access to the app that runs this script:

1. Open System Settings.
2. Go to Privacy & Security > Full Disk Access.
3. Click the + button or enable the existing entry.
4. Add or enable the app you use to run Python:
   - Terminal.app if you run from Terminal.
   - iTerm.app if you run from iTerm.
   - Visual Studio Code.app if you run from VS Code's integrated terminal.
   - Codex or another editor app if it launches the script.
5. Quit that app completely and open it again. A new terminal window is not always enough.
6. Rerun:
   python3 scripts/explore_libraries.py --library ~/Pictures/"Photos Library.photoslibrary"

If it still says `not-readable`, also check System Settings > Privacy & Security > Files and Folders and allow access to Pictures or Removable Volumes where applicable.
"""


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
            "\n\n"
            f"{FULL_DISK_ACCESS_HELP}"
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
            f"{FULL_DISK_ACCESS_HELP}\nDetails: {details}"
        )
    return roots
