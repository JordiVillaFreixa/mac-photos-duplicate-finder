# Mac Photos Duplicate Finder

Python scripts for safely inspecting macOS Photos libraries and finding exact or probable duplicate photo and video files.

The project is intentionally conservative:

- It never writes to `Photos.sqlite`.
- It never deletes media files.
- It never moves files inside a `.photoslibrary` package.
- Exact duplicate detection is based on file bytes using SHA-256 hashes.
- Probable photo duplicate detection uses perceptual image hashing and always requires manual review.
- By default, the scripts only read files and write reports outside the Photos library.

## Requirements

- macOS.
- Python 3.8 or newer.
- Full Disk Access may be required for Terminal, iTerm, VS Code, or Codex if macOS denies access to `~/Pictures` or external drives.

Exact duplicate detection has no third-party Python dependencies. Probable duplicate detection requires Pillow because Python's standard library cannot safely decode common photo formats.

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

### 3. Find probable duplicate photos

Install Pillow in your environment:

```bash
python3 -m pip install Pillow
```

Then run:

```bash
python3 scripts/find_probable_duplicates.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --output-dir reports/probable-duplicates
```

This creates:

- `probable_duplicate_pairs.json`: machine-readable candidate pairs.
- `probable_duplicate_proposal.csv`: review table.
- `probable_safety_report.txt`: safety summary.
- `probable_skipped_files.txt`: images that could not be decoded.

The script only scans photos, not videos. It uses a dHash perceptual hash and reports image pairs whose Hamming distance is at or below `--max-distance` (`6` by default). Lower values are stricter. Values above `12` are refused because they are likely to create too many false positives.

Every probable pair must be reviewed manually. A perceptual hash is useful for finding candidates, but it is not proof that two photos are duplicates.

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
