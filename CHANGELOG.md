# CHANGELOG

## v1.0.0 (2023-10-01) - Initial Release
- Parser-backed YAML syntax validation (Phase 1).
- Structural schema checks for GitHub Actions (Phase 2: on, jobs, permissions, strategy).
- Heuristic linting with warnings (Phase 3: tabs, unclosed strings, empty jobs).
- Batch mode for repo-wide validation.
- Versioned JSON output with schema contract.
- CI annotations (stderr, GitHub-native).
- Unit tests for core functionality.
- Packaging: GitHub CLI extension + PyPI.
