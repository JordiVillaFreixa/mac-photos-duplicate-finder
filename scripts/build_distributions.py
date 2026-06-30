#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "downloads"
PACKAGE_NAME = "mac-photos-duplicate-finder"
VERSION_FILE = PROJECT_ROOT / "VERSION"
PYPROJECT_FILE = PROJECT_ROOT / "pyproject.toml"
README_FILE = PROJECT_ROOT / "README.md"
SITE_INDEX_FILE = PROJECT_ROOT / "docs" / "index.html"

INCLUDE_PATHS = [
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "VERSION",
    "pyproject.toml",
    "scripts",
    "src",
    "tests",
]


@dataclass
class Distribution:
    filename: str
    format: str
    size_bytes: int
    sha256: str
    url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build downloadable source distributions for the GitHub Pages site."
    )
    parser.add_argument(
        "--version",
        help="Distribution version label. Default: value from VERSION.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where downloadable archives and manifest will be written.",
    )
    parser.add_argument(
        "--release-notes",
        type=Path,
        help="Optional Markdown file with release notes for manifest metadata.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    version = args.version or read_version()
    sync_project_version(version)
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{PACKAGE_NAME}-{version}"
    zip_path = output_dir / f"{prefix}.zip"
    tar_path = output_dir / f"{prefix}.tar.gz"

    files = sorted(iter_distribution_files())
    write_zip(zip_path, prefix, files)
    write_tar_gz(tar_path, prefix, files)

    distributions = [
        describe_distribution(zip_path, "zip"),
        describe_distribution(tar_path, "tar.gz"),
    ]
    manifest = {
        "name": PACKAGE_NAME,
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_notes": read_release_notes(args.release_notes, version),
        "distributions": [asdict(distribution) for distribution in distributions],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_releases_manifest(output_dir, manifest)

    checksums = [
        f"{distribution.sha256}  {distribution.filename}"
        for distribution in distributions
    ]
    (output_dir / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")

    print(f"Wrote {len(distributions)} distributions to {output_dir}")
    for distribution in distributions:
        print(f"- {distribution.filename} | {distribution.size_bytes} bytes | {distribution.sha256}")
    return 0


def read_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def sync_project_version(version: str) -> None:
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")
    update_file(PYPROJECT_FILE, r'version = "[^"]+"', f'version = "{version}"')
    update_file(
        README_FILE,
        r"python3 scripts/build_distributions.py --version [0-9]+\.[0-9]+\.[0-9]+",
        f"python3 scripts/build_distributions.py --version {version}",
    )
    update_file(
        README_FILE,
        r"mac-photos-duplicate-finder-[0-9]+\.[0-9]+\.[0-9]+",
        f"mac-photos-duplicate-finder-{version}",
    )
    update_file(
        SITE_INDEX_FILE,
        r"mac-photos-duplicate-finder-[0-9]+\.[0-9]+\.[0-9]+",
        f"mac-photos-duplicate-finder-{version}",
    )


def update_file(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated = re.sub(pattern, replacement, text)
    if updated != text:
        path.write_text(updated, encoding="utf-8")


def read_release_notes(path: Path | None, version: str) -> str:
    if path is not None:
        return path.read_text(encoding="utf-8").strip()
    return changelog_section(version)


def write_releases_manifest(output_dir: Path, manifest: dict[str, object]) -> None:
    releases_path = output_dir / "releases.json"
    if releases_path.exists():
        releases = json.loads(releases_path.read_text(encoding="utf-8"))
    else:
        releases = {"name": PACKAGE_NAME, "releases": []}

    existing = [
        release
        for release in releases.get("releases", [])
        if release.get("version") != manifest["version"]
    ]
    existing.insert(0, manifest)
    releases["releases"] = sorted(
        existing_discovered_releases(output_dir, existing),
        key=lambda release: release.get("version", ""),
        reverse=True,
    )
    releases_path.write_text(json.dumps(releases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def existing_discovered_releases(
    output_dir: Path,
    known_releases: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_version = {str(release.get("version")): release for release in known_releases}
    for zip_path in output_dir.glob(f"{PACKAGE_NAME}-*.zip"):
        version = zip_path.name.removeprefix(f"{PACKAGE_NAME}-").removesuffix(".zip")
        tar_path = output_dir / f"{PACKAGE_NAME}-{version}.tar.gz"
        if version in by_version or not tar_path.exists():
            continue
        distributions = [
            asdict(describe_distribution(zip_path, "zip")),
            asdict(describe_distribution(tar_path, "tar.gz")),
        ]
        by_version[version] = {
            "name": PACKAGE_NAME,
            "version": version,
            "generated_at": "",
            "release_notes": changelog_section(version),
            "distributions": distributions,
        }
    return list(by_version.values())


def changelog_section(version: str) -> str:
    changelog_path = PROJECT_ROOT / "CHANGELOG.md"
    if not changelog_path.exists():
        return ""
    changelog = changelog_path.read_text(encoding="utf-8")
    match = re.search(
        rf"^## {re.escape(version)}[^\n]*\n(?P<body>.*?)(?=^## |\Z)",
        changelog,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group("body").strip() if match else ""


def iter_distribution_files() -> list[Path]:
    files: list[Path] = []
    for include_path in INCLUDE_PATHS:
        path = PROJECT_ROOT / include_path
        if path.is_file():
            files.append(path)
            continue
        for child in path.rglob("*"):
            if child.is_file() and should_include(child):
                files.append(child)
    return files


def should_include(path: Path) -> bool:
    parts = set(path.relative_to(PROJECT_ROOT).parts)
    excluded = {
        ".git",
        ".codex",
        "__pycache__",
        ".pytest_cache",
        "reports",
        "docs",
        "dist",
        "build",
    }
    return not parts.intersection(excluded) and path.suffix != ".pyc"


def write_zip(path: Path, prefix: str, files: list[Path]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            relative = file_path.relative_to(PROJECT_ROOT)
            archive.write(file_path, f"{prefix}/{relative}")


def write_tar_gz(path: Path, prefix: str, files: list[Path]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for file_path in files:
            relative = file_path.relative_to(PROJECT_ROOT)
            archive.add(file_path, arcname=f"{prefix}/{relative}")


def describe_distribution(path: Path, archive_format: str) -> Distribution:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return Distribution(
        filename=path.name,
        format=archive_format,
        size_bytes=path.stat().st_size,
        sha256=digest,
        url=f"downloads/{path.name}",
    )


if __name__ == "__main__":
    raise SystemExit(main())
