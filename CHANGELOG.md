## [2.2.2] - 2026-03-29

### Fixed
- XDG vs ~/.herald path mismatch between setup.sh and cli.py (#5)
- Preset resolution: feeds/sources key mismatch, missing id generation (#6)
- Pipeline preset path resolution to project root
- run.sh always reporting success status
- story_type not persisted in clustering
- URL dedup mismatch for empty paths
- Tavily API key not read from config
- Schedule time validation accepting invalid hours
- systemd scheduler fallback to cron on failure
- Mirror detection using substring instead of hostname match
- Topic config shape normalization
- Command injection in news-add docs
- Stale path references in command docs

## [2.2.1] - 2026-03-19

## [2.1.1] - 2026-03-17

## [2.2.0] - 2026-03-19

# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.0.0] - 2026-03-05

Complete rewrite: agent-native news intelligence layer.

### Added
- SQLite database with WAL, FTS5 full-text search
- Story clustering — title similarity, merge guards, canonical re-election
- Topic extraction as standalone module
- Multi-adapter collection: RSS, HN, Tavily with retry and fault isolation
- URL canonicalization (10 normalization rules)
- Scoring formulas for articles and stories
- Project stage — markdown brief generation from stories
- Pipeline orchestrator: collect → ingest → cluster → project
- CLI entry point: init, run, brief, status subcommands
- ULID-based model identifiers

### Fixed
- BSD grep compatibility (macOS `grep -oP` → `sed`)
- SessionStart hook path (XDG data directory)
- Scoring formulas and merge guard description in README
- Adapter map wiring from config, source sync to DB

### Changed
- Full v2 architecture replacing v1 RSS-only approach
- Plugin commands, hooks, and skill updated for v2
- README rewritten for v2

## [1.0.0] - 2026-02-20

Initial release. RSS feed aggregation with basic deduplication.
