from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .duplicates import iter_media_files
from .media_types import PHOTO_EXTENSIONS


@dataclass
class ProbableImage:
    path: str
    relative_path: str
    size_bytes: int
    dhash: str


@dataclass
class ProbableDuplicatePair:
    first_path: str
    second_path: str
    first_size_bytes: int
    second_size_bytes: int
    first_dhash: str
    second_dhash: str
    hamming_distance: int


@dataclass
class BKNode:
    digest: int
    image: ProbableImage
    children: dict[int, "BKNode"]


def require_pillow():
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "Probable duplicate detection requires Pillow. Install it in your environment with "
            "`python3 -m pip install Pillow`, then rerun this script. No Photos library changes "
            "were made."
        ) from exc
    return Image, ImageOps


def hamming_distance(first: int, second: int) -> int:
    return bin(first ^ second).count("1")


def dhash_image(path: Path, hash_size: int = 8) -> int:
    Image, ImageOps = require_pillow()
    with Image.open(path) as image:
        grayscale = ImageOps.exif_transpose(image).convert("L")
        resized = grayscale.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)

    bits = 0
    for row in range(hash_size):
        for column in range(hash_size):
            left = resized.getpixel((column, row))
            right = resized.getpixel((column + 1, row))
            bits = (bits << 1) | int(left > right)
    return bits


def iter_probable_images(library: Path, scan_all_media: bool = False) -> list[Path]:
    return [
        path
        for path in iter_media_files(library, scan_all_media=scan_all_media)
        if path.suffix.lower() in PHOTO_EXTENSIONS
    ]


def find_probable_duplicate_pairs(
    library_path: Path,
    max_distance: int = 6,
    scan_all_media: bool = False,
) -> tuple[list[ProbableDuplicatePair], list[str]]:
    library = library_path.expanduser().resolve()
    images: list[ProbableImage] = []
    errors: list[str] = []

    for path in iter_probable_images(library, scan_all_media=scan_all_media):
        try:
            digest = dhash_image(path)
            size = path.stat().st_size
            images.append(
                ProbableImage(
                    path=str(path),
                    relative_path=str(path.relative_to(library)),
                    size_bytes=size,
                    dhash=f"{digest:016x}",
                )
            )
        except Exception as exc:  # Pillow can raise format-specific decoding errors.
            errors.append(f"Skipped {path}: {exc}")

    pairs = _find_pairs_with_bk_tree(images, max_distance)

    pairs.sort(key=lambda pair: (pair.hamming_distance, pair.first_path, pair.second_path))
    return pairs, errors


def _find_pairs_with_bk_tree(
    images: list[ProbableImage],
    max_distance: int,
) -> list[ProbableDuplicatePair]:
    root: BKNode | None = None
    pairs: list[ProbableDuplicatePair] = []

    for image in images:
        digest = int(image.dhash, 16)
        if root is None:
            root = BKNode(digest=digest, image=image, children={})
            continue

        for candidate, distance in _query_bk_tree(root, digest, max_distance):
            pairs.append(
                ProbableDuplicatePair(
                    first_path=candidate.path,
                    second_path=image.path,
                    first_size_bytes=candidate.size_bytes,
                    second_size_bytes=image.size_bytes,
                    first_dhash=candidate.dhash,
                    second_dhash=image.dhash,
                    hamming_distance=distance,
                )
            )
        _insert_bk_tree(root, digest, image)

    return pairs


def _insert_bk_tree(root: BKNode, digest: int, image: ProbableImage) -> None:
    node = root
    while True:
        distance = hamming_distance(digest, node.digest)
        child = node.children.get(distance)
        if child is None:
            node.children[distance] = BKNode(digest=digest, image=image, children={})
            return
        node = child


def _query_bk_tree(
    root: BKNode,
    digest: int,
    max_distance: int,
) -> list[tuple[ProbableImage, int]]:
    matches: list[tuple[ProbableImage, int]] = []
    stack = [root]
    while stack:
        node = stack.pop()
        distance = hamming_distance(digest, node.digest)
        if distance <= max_distance:
            matches.append((node.image, distance))

        lower = distance - max_distance
        upper = distance + max_distance
        for edge_distance, child in node.children.items():
            if lower <= edge_distance <= upper:
                stack.append(child)
    return matches


def write_probable_duplicate_reports(
    pairs: list[ProbableDuplicatePair],
    errors: list[str],
    output_dir: Path,
    library: Path,
    max_distance: int,
    scan_all_media: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "probable_duplicate_pairs.json").write_text(
        json.dumps([asdict(pair) for pair in pairs], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with (output_dir / "probable_duplicate_proposal.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "recommended_action",
                "hamming_distance",
                "first_path",
                "second_path",
                "first_size_bytes",
                "second_size_bytes",
                "first_dhash",
                "second_dhash",
                "target_review_album",
            ],
        )
        writer.writeheader()
        for pair in pairs:
            writer.writerow(
                {
                    "recommended_action": "manual_review_required",
                    "hamming_distance": pair.hamming_distance,
                    "first_path": pair.first_path,
                    "second_path": pair.second_path,
                    "first_size_bytes": pair.first_size_bytes,
                    "second_size_bytes": pair.second_size_bytes,
                    "first_dhash": pair.first_dhash,
                    "second_dhash": pair.second_dhash,
                    "target_review_album": "Duplicats probables",
                }
            )

    safety = [
        "Safety report",
        "=============",
        "",
        f"Library scanned: {library}",
        f"Scan mode: {'all media in package' if scan_all_media else 'originals/Masters only'}",
        f"Max dHash Hamming distance: {max_distance}",
        f"Probable duplicate pairs found: {len(pairs)}",
        f"Files skipped because they could not be decoded: {len(errors)}",
        "",
        "No Photos database was edited.",
        "No file was deleted.",
        "No file was moved inside the Photos library.",
        "",
        "These are probable duplicates, not confirmed duplicates. Review every pair manually",
        "in Photos.app before deleting, merging, or moving anything.",
    ]
    (output_dir / "probable_safety_report.txt").write_text(
        "\n".join(safety) + "\n", encoding="utf-8"
    )
    (output_dir / "probable_skipped_files.txt").write_text(
        "\n".join(errors) + ("\n" if errors else ""), encoding="utf-8"
    )
