# Mac Photos Duplicate Finder

Python scripts for inspecting macOS Photos libraries, finding exact or probable duplicate photo and video files, and preparing review albums inside Photos.

The project is intentionally conservative. Its default behavior is to read library data, write reports outside the Photos package, and leave destructive decisions to the person using Photos:

- It never writes to `Photos.sqlite`.
- It never deletes media files.
- It never moves files inside a `.photoslibrary` package.
- Exact duplicate detection is based on file bytes using SHA-256 hashes.
- Probable photo duplicate detection uses perceptual image hashing and always requires manual review.
- By default, the scripts only read files and write reports outside the Photos library.

## Disclaimer

This project is shared **as is**, with no warranty. macOS Photos libraries are complex database-backed packages, and mistakes can affect local libraries, iCloud Photos sync, albums, edits, metadata, or deleted items.

Use these scripts only if you understand what each command does. Keep backups before acting on any deletion proposal. The author does not take responsibility for damage, data loss, sync problems, incorrect duplicate decisions, or any other issue caused by using or modifying these scripts. The responsibility for reviewing the reports and using the scripts correctly is yours.

The scripts are designed to avoid direct library mutation, but the final decision to delete, merge, or otherwise change Photos items must be made carefully inside Photos.

## License and copyright

Copyright (c) 2026 Jordi Villà.

This project is released under the MIT License. You may use, copy, modify, publish, distribute, sublicense, and sell copies of the software, as long as the original copyright notice and MIT license text are included in all copies or substantial portions of the software. See `LICENSE`.

## Requirements

- macOS.
- Python 3.8 or newer.
- Full Disk Access may be required for Terminal, iTerm, VS Code, or Codex if macOS denies access to `~/Pictures` or external drives.

Exact duplicate detection has no third-party Python dependencies. Probable duplicate detection requires Pillow because Python's standard library cannot safely decode common photo formats.

## Website and downloads

The public project website lives in `docs/` and is ready for GitHub Pages. It includes a static landing page, SEO metadata, Open Graph/Twitter tags, `robots.txt`, `sitemap.xml`, and direct links to downloadable source distributions.

To create a new downloadable release, update `VERSION` and `CHANGELOG.md`, then regenerate the archives:

```bash
python3 scripts/build_distributions.py --version 0.3.1
```

This writes:

- `docs/downloads/mac-photos-duplicate-finder-0.3.1.zip`
- `docs/downloads/mac-photos-duplicate-finder-0.3.1.tar.gz`
- `docs/downloads/SHA256SUMS.txt`
- `docs/downloads/manifest.json`

Release notes are taken from the matching section in `CHANGELOG.md` and written into `manifest.json`. You can override them with `--release-notes path/to/notes.md`.

GitHub Pages deployment is configured in `.github/workflows/pages.yml`. In the repository settings, enable GitHub Pages with GitHub Actions as the source.

## GitHub Pages custom domain

The site is configured for the custom domain `mac-photos-duplicate-finder.org`. The repository contains `docs/CNAME`, but because this project deploys Pages through GitHub Actions, the custom domain still must be configured in GitHub repository Settings > Pages and the DNS records must exist at the domain provider.

If GitHub shows `InvalidDNSError`, DNS is not resolving. Add these records at the DNS provider:

```text
mac-photos-duplicate-finder.org.  A     185.199.108.153
mac-photos-duplicate-finder.org.  A     185.199.109.153
mac-photos-duplicate-finder.org.  A     185.199.110.153
mac-photos-duplicate-finder.org.  A     185.199.111.153
```

Optional IPv6 records:

```text
mac-photos-duplicate-finder.org.  AAAA  2606:50c0:8000::153
mac-photos-duplicate-finder.org.  AAAA  2606:50c0:8001::153
mac-photos-duplicate-finder.org.  AAAA  2606:50c0:8002::153
mac-photos-duplicate-finder.org.  AAAA  2606:50c0:8003::153
```

For the alternate `www` name:

```text
www.mac-photos-duplicate-finder.org.  CNAME  jordivillafreixa.github.io.
```

Do not include the repository name in the `www` CNAME target. After DNS propagates, run:

```bash
dig +short mac-photos-duplicate-finder.org A
dig +short www.mac-photos-duplicate-finder.org CNAME
```

GitHub can only provision HTTPS after these DNS records resolve and the Pages custom domain check passes. Until then, `Enforce HTTPS` remains unavailable.

## GitHub Releases

Files in `docs/downloads/` are linked from the website, but they do not automatically appear under the GitHub repository's Releases tab. GitHub Releases are created by `.github/workflows/release.yml`.

To publish a release:

1. Update `VERSION`.
2. Add a matching section to `CHANGELOG.md`, for example `## 0.3.0 - YYYY-MM-DD`.
3. Push a tag:

```bash
git tag v0.3.0
git push origin v0.3.0
```

The workflow builds the ZIP and tar.gz distributions, creates or updates the GitHub Release, and uploads the archives, `SHA256SUMS.txt`, `manifest.json`, and `releases.json`. You can also run the workflow manually from GitHub Actions and provide a version.

## macOS Privacy Access

If `explore_libraries.py` reports a library as `not-readable`, duplicate detection cannot work reliably. A result such as `originals=0 photos=0 videos=0` is not meaningful until the library is readable.

Grant Full Disk Access to the app that runs Python:

1. Open System Settings.
2. Go to Privacy & Security > Full Disk Access.
3. Click the `+` button, or enable the existing entry if it is already listed.
4. Add or enable the correct app:
   - `Terminal.app` if you run commands from Terminal.
   - `iTerm.app` if you run commands from iTerm.
   - `Visual Studio Code.app` if you run commands from VS Code's integrated terminal.
   - `Codex` or another editor app if that app launches the script.
5. Quit that app completely and open it again. Opening a new terminal tab is not always enough.
6. Rerun:

```bash
python3 scripts/explore_libraries.py \
  --library ~/Pictures/"Photos Library.photoslibrary"
```

Expected result after access is fixed: the library should no longer be `not-readable`, and `originals`, `photos`, or `videos` should reflect the actual contents.

If it still says `not-readable`, also check System Settings > Privacy & Security > Files and Folders and allow access to Pictures or Removable Volumes where applicable.

## Typical workflow

A safe workflow is:

1. Inventory the Photos library and confirm it is readable.
2. Generate duplicate reports.
3. Optionally re-rank exact duplicates so the best copy is kept.
4. Create a Photos album containing only the copies proposed for review.
5. Review inside Photos before deleting anything.

Do not skip the review step. An album created by these scripts is a decision aid, not proof that deleting everything in it is appropriate for every library.

## Creating duplicate review albums inside Photos

The project can create normal Photos albums that contain the duplicate candidates from the generated CSV reports. This is the safest supported way to bring the result back into Photos: the script asks Photos.app to create or reuse an album and add existing media items by their Photos asset IDs.

It does **not** create or edit the built-in Photos `Duplicates` smart section. It also does not import files, move files, delete files, or write to `Photos.sqlite`.

There are two useful album workflows:

### Basic exact-duplicate album

Use this when you want an album containing the duplicate candidates from the first SHA-256 report:

```bash
python3 scripts/create_photos_review_album.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --proposal-csv reports/duplicates/duplicate_proposal.csv \
  --album-name "Duplicats candidats" \
  --output-dir reports/photos-album
```

This first command is a dry run. It maps file paths from the CSV to Photos asset IDs and writes:

- `reports/photos-album/photos_album_plan.json`
- `reports/photos-album/photos_album_asset_ids.txt`
- `reports/photos-album/create_photos_album.applescript`
- `reports/photos-album/photos_album_report.txt`

If `photos_album_report.txt` says there are `0` unmapped paths, run the same command with `--execute`:

```bash
python3 scripts/create_photos_review_album.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --proposal-csv reports/duplicates/duplicate_proposal.csv \
  --album-name "Duplicats candidats" \
  --output-dir reports/photos-album \
  --execute \
  --batch-size 100 \
  --batch-timeout 120
```

The album `Duplicats candidats` contains only `duplicate_candidate_path` items from the CSV. It does not include the `keep_path` items unless you explicitly pass `--include-kept`.

### Quality-ranked lower-quality album

Use this when you want to keep the best detected Photos asset in every exact-duplicate group and put the lower-quality copies in an album:

```bash
python3 scripts/rerank_exact_duplicates_by_quality.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --duplicate-groups reports/duplicates/duplicate_groups.json \
  --output-dir reports/duplicates-low-quality
```

Then create the Photos album from that quality-ranked proposal:

```bash
python3 scripts/create_photos_review_album.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --proposal-csv reports/duplicates-low-quality/duplicate_proposal.csv \
  --album-name "Lower-Quality Duplicate Candidates" \
  --output-dir reports/photos-album-low-quality \
  --execute \
  --batch-size 100 \
  --batch-timeout 120
```

This is usually the better album to review before deleting exact duplicates, because the `keep` file is selected by quality criteria instead of by path order.

### How Photos album creation works

The album script reads `Photos.sqlite` in immutable read-only mode only to map original file paths to Photos asset IDs. It then controls Photos through AppleScript. On the first run, macOS may ask for Automation permission so that Terminal, VS Code, or the app running Python can control Photos.

Large albums are processed in batches. With `--batch-size 100`, an album with 17,914 mapped assets is processed as 180 AppleScript batches. The script prints progress like:

```text
Adding batch 42/180 (100 assets)...
```

If Photos is slow, reduce `--batch-size` to `50` or increase `--batch-timeout` to `300`. If a few Photos asset IDs cannot be resolved through AppleScript, the script reports them as failures; review those manually.

Important Photos behavior:

- Removing an item from an album only removes it from that album.
- Deleting an item from the library deletes it from the Photos library and may affect iCloud Photos and synced devices.
- The generated albums are review aids. They are not automatic deletion instructions.

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

Parameters:

- `--output`: JSON file to write. Default: `reports/libraries.json`.
- `--search-dir`: directory to search recursively for `.photoslibrary` packages. You can pass it more than once.
- `--library`: inspect one specific `.photoslibrary`.

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

Important detail: the default proposal keeps one file per SHA-256 group using a deterministic path order. That is safe and repeatable, but it does not mean the kept copy is the best Photos asset. If you want to prefer the copy with more pixels or better Photos metadata, run the quality re-ranking step below.

Parameters:

- `--library`: required path to the `.photoslibrary`.
- `--output-dir`: where reports are written. Default: `reports/duplicates`.
- `--scan-all-media`: scans the whole package instead of only `originals`/`Masters`. Use this carefully because it may include derivatives, previews, or internal resources.
- `--copy-candidates-to`: copies duplicate candidate files to an external review folder. It refuses destinations inside the Photos package.

### 3. Re-rank exact duplicates by quality

Exact byte duplicates can still have different Photos asset metadata. For example, two files may be byte-identical but Photos may know different dimensions, capture metadata, or location metadata for the asset records.

To keep the best available copy according to Photos metadata:

```bash
python3 scripts/rerank_exact_duplicates_by_quality.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --duplicate-groups reports/duplicates/duplicate_groups.json \
  --output-dir reports/duplicates-low-quality
```

This creates:

- `duplicate_groups_by_quality.json`: duplicate groups with a quality-ranked `keep`.
- `duplicate_proposal.csv`: lower-quality duplicate candidates to review.
- `quality_safety_report.txt`: criteria and safety summary.

Ranking criteria:

1. Higher pixel count: `ZWIDTH * ZHEIGHT` from Photos metadata.
2. Higher metadata score: capture date and real location metadata.
3. If quality is tied, preserve the previous `keep` so the script does not change decisions arbitrarily.

Parameters:

- `--library`: required path to the `.photoslibrary`.
- `--duplicate-groups`: JSON produced by `find_exact_duplicates.py`. Default: `reports/duplicates/duplicate_groups.json`.
- `--output-dir`: where the quality-ranked reports are written. Default: `reports/duplicates-low-quality`.

### 4. Find probable duplicate photos

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

For a short smoke test with visible progress:

```bash
python3 scripts/find_probable_duplicates.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --output-dir reports/probable-duplicates-test \
  --limit 200 \
  --progress-every 25
```

Progress output includes the number of scanned photos and the completion percentage, for example `Scanned 75/200 photos (37.5%)`.

This creates:

- `probable_duplicate_pairs.json`: machine-readable candidate pairs.
- `probable_duplicate_proposal.csv`: review table.
- `probable_safety_report.txt`: safety summary.
- `probable_skipped_files.txt`: images that could not be decoded.

The script only scans photos, not videos. It uses a dHash perceptual hash and reports image pairs whose Hamming distance is at or below `--max-distance` (`6` by default). Lower values are stricter. Values above `12` are refused because they are likely to create too many false positives.

Every probable pair must be reviewed manually. A perceptual hash is useful for finding candidates, but it is not proof that two photos are duplicates.

Parameters:

- `--library`: required path to the `.photoslibrary`.
- `--output-dir`: where reports are written. Default: `reports/probable-duplicates`.
- `--max-distance`: maximum dHash Hamming distance. Lower is stricter. Default: `6`. Values above `12` are refused.
- `--scan-all-media`: scans all photo-looking files in the package instead of only originals.
- `--limit`: scan only the first N photos. Useful for smoke tests.
- `--progress-every`: print progress every N scanned photos. Use `0` to disable progress updates.

### 5. Create a Photos review album

After generating a duplicate proposal CSV, you can create a normal Photos album for manual review:

```bash
python3 scripts/create_photos_review_album.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --proposal-csv reports/duplicates/duplicate_proposal.csv \
  --album-name "Duplicats candidats"
```

By default this is a dry run. It does not modify Photos. It writes:

- `photos_album_plan.json`: mapped Photos asset IDs.
- `photos_album_asset_ids.txt`: one Photos asset ID per line.
- `create_photos_album.applescript`: the AppleScript that would be executed.
- `photos_album_report.txt`: safety summary and any unmapped paths.

To actually create or update the album through Photos.app automation, add `--execute`:

```bash
python3 scripts/create_photos_review_album.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --proposal-csv reports/duplicates/duplicate_proposal.csv \
  --album-name "Duplicats candidats" \
  --execute
```

The script reads `Photos.sqlite` only in immutable read-only mode to map original file paths to existing Photos asset IDs. It does not edit the database, import files, delete files, or move anything inside the Photos library. macOS may ask for Automation permission the first time Python controls Photos.

For the quality-ranked album:

```bash
python3 scripts/create_photos_review_album.py \
  --library ~/Pictures/"Photos Library.photoslibrary" \
  --proposal-csv reports/duplicates-low-quality/duplicate_proposal.csv \
  --album-name "Lower-Quality Duplicate Candidates" \
  --output-dir reports/photos-album-low-quality \
  --execute
```

This is the safer album to use when your goal is to delete lower-quality copies while keeping the best detected Photos asset in each exact-duplicate group.

Large albums are added to Photos in batches. The default batch size is `100`, so an album with 17,914 assets is processed as 180 batches. The script prints progress such as `Adding batch 42/180 (100 assets)...`.

Parameters:

- `--library`: required path to the `.photoslibrary`.
- `--proposal-csv`: CSV produced by exact, quality-ranked, or probable duplicate scripts.
- `--album-name`: Photos album to create or reuse.
- `--output-dir`: where the plan, AppleScript, ID list, and report are written.
- `--id-source`: Photos ID field to use. Default: `uuid`. Alternative: `cloud_asset_guid`.
- `--include-kept`: for exact duplicate CSVs, include the `keep_path` files too. Do not use this if the album is meant to contain only deletion candidates.
- `--execute`: actually controls Photos and creates or updates the album. Without it, the command is a dry run.
- `--batch-size`: number of assets per AppleScript batch. Default: `100`. Smaller values are slower but easier for Photos to process; larger values may be faster but can make Photos appear busy for longer.
- `--batch-timeout`: seconds to wait for each AppleScript batch. Default: `120`. Increase it if Photos is slow or the Mac is under load.

Warnings:

- Removing an item from an album does not delete it from the library.
- Deleting an item from the library may delete it from iCloud Photos and synced devices.
- Review the album before deleting. A script can identify candidates, but you are responsible for the final action.
- If Photos cannot resolve some asset IDs through AppleScript, the script reports them as failures. Review those manually.

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
