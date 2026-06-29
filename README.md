# Mac Photos Duplicate Finder

Python scripts for safely inspecting macOS Photos libraries and finding exact duplicate photo or video files.

The project is intentionally conservative:

- It never writes to `Photos.sqlite`.
- It never deletes media files.
- It never moves files inside a `.photoslibrary` package.
- Duplicate detection is based on exact file bytes using SHA-256 hashes.
- By default, the scripts only read files and write reports outside the Photos library.

## Requirements

- macOS.
- Python 3.10 or newer.
- Full Disk Access may be required for Terminal, iTerm, VS Code, or Codex if macOS denies access to `~/Pictures` or external drives.

No third-party Python dependencies are required.

## Scripts

### 1. Explore Photos libraries

```bash
python3 scripts/explore_libraries.py --output reports/libraries.json
```

Useful options:

```bash
python3 scripts/explore_libraries.py --search-dir ~/Pictures --search-dir /Volumes --output reports/libraries.json
python3 scripts/explore_libraries.py --library ~/Pictures/"Photos Library.photoslibrary" --output reports/libraries.json
```

The report includes access status, approximate package size, total files, count of original photos, count of original videos, and database presence. If a library cannot be read, the script records the error instead of failing destructively.

### 2. Find exact duplicate media

```bash
python3 scripts/find_exact_duplicates.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --output-dir reports/duplicates
```

This creates:

- `duplicate_groups.json`: machine-readable duplicate groups.
- `duplicate_proposal.csv`: review table with one kept file and duplicate candidates.
- `safety_report.txt`: clear explanation of what was scanned and what was not modified.

The generated proposal is a review artifact. It is not an automatic Photos mutation. To keep Photos safe, move duplicates through the Photos app only after manual review, or use the app's built-in duplicate handling where available.

## Optional review copies

For manual inspection outside Photos, you can copy duplicate candidates to a separate folder:

```bash
python3 scripts/find_exact_duplicates.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --output-dir reports/duplicates \
  --copy-candidates-to ~/Pictures/photos-duplicate-review
```

This copies duplicate candidate files outside the Photos library. It still does not move, delete, or edit the Photos library.

## Why not move files into the Photos package?

Photos libraries are database-backed packages. Moving files directly inside the package can corrupt references, thumbnails, edits, iCloud sync state, or the whole library. This tool stops short of that boundary. If a future workflow needs to create a Photos album named `Duplicats`, it should use Apple-supported automation or the Photos UI, never direct file manipulation inside the package.

## Development

Run tests:

```bash
python3 -m unittest discover -s tests
```

