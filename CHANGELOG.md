# Changelog

All notable project distribution changes are documented here.

## 0.3.1 - 2026-06-30

### Added

- Copy buttons for command snippets on the GitHub Pages site.

### Changed

- Refined the website toward a more professional product-style presentation.
- Removed the public custom-domain setup page from the website and sitemap.

## 0.3.0 - 2026-06-30

### Changed

- Renamed the quality-ranked Photos album from `Duplicats més baixa qualitat` to `Lower-Quality Duplicate Candidates`.
- Updated README, website examples, generated low-quality duplicate CSV reports, and Photos album plans to use the new English album name.

## 0.2.0 - 2026-06-30

### Added

- GitHub Pages website under `docs/` with SEO metadata, Open Graph/Twitter cards, sitemap, robots file, and download links.
- Downloadable ZIP and tar.gz source distributions with SHA-256 checksums and a JSON manifest.
- Versioning workflow based on `VERSION`, `CHANGELOG.md`, and generated release metadata.
- GitHub Releases workflow that builds distributions and uploads release assets.
- Custom domain documentation for `mac-photos-duplicate-finder.org` and its `www` alternate.
- Quality-ranked duplicate workflow that keeps the best detected Photos asset by pixel count and metadata.
- Photos review album automation with batch processing and timeout controls.
- Copyright notice for Jordi Villà.

### Changed

- README now includes a fuller narrative workflow, parameter explanations, safety warnings, and as-is disclaimer.
- Distribution downloads are linked from the GitHub Pages site instead of being ad hoc local artifacts.

## 0.1.0 - 2026-06-29

### Added

- Initial safe Python scripts for inspecting Photos libraries.
- Exact duplicate detection by SHA-256.
- Probable duplicate photo detection by perceptual dHash.
- Read-only reports and safety summaries.
