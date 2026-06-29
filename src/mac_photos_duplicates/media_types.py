from __future__ import annotations

from pathlib import Path

PHOTO_EXTENSIONS = {
    ".arw",
    ".bmp",
    ".cr2",
    ".cr3",
    ".dng",
    ".gif",
    ".heic",
    ".heif",
    ".jpeg",
    ".jpg",
    ".nef",
    ".orf",
    ".png",
    ".raf",
    ".raw",
    ".rw2",
    ".tif",
    ".tiff",
    ".webp",
}

VIDEO_EXTENSIONS = {
    ".3gp",
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".mts",
    ".mxf",
    ".wmv",
}

MEDIA_EXTENSIONS = PHOTO_EXTENSIONS | VIDEO_EXTENSIONS


def media_kind(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in PHOTO_EXTENSIONS:
        return "photo"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return None

