# Changelog

All notable project distribution changes are documented here.

## 0.2.0 - 2026-06-30

### Added

- GitHub Pages website under `docs/` with SEO metadata, Open Graph/Twitter cards, sitemap, robots file, and download links.
- Downloadable ZIP and tar.gz source distributions with SHA-256 checksums and a JSON manifest.
- Versioning workflow based on `VERSION`, `CHANGELOG.md`, and generated release metadata.
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
