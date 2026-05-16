# Changelog
All notable changes to **infisical-conf** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-05-16
### Added
- Initial public release of **infisical-conf**.
- Core `InfisicalManager` class with:
  - Local hierarchical cache
  - Wildcard pull/get/drop operations
  - Explicit set/push operations
  - Dirty‑tracking for set updates and new secrets
  - Automatic folder creation (within allowed projects)
  - Strict notation validation (`project.folder.secret`)
  - Visual diagnostics (Rich tables, trees, project listings)
  - Clean, aligned logging with optional secret redaction
- Full read-only mode (`readonly=True`) to prevent any push operations.
- Django integration examples:
  - Feature flag loader
  - Startup cache warm‑up
  - Toggle views
  - Settings loader pattern
- Dynamic environment selection (`set_env`)
- Visualisation helpers:
  - Cache tree
  - Dirty tree
  - Project table
  - Cache status table
- Complete documentation and usage scenarios:
  - Static config loads
  - Dynamic flags
  - Django settings integration
  - Visualisation examples

### Notes
- This release wraps the official `infisical-sdk` with a higher‑level, safe, more ergonomic workflow.
- Designed for reproducible configuration workflows in homelab and development environments.

---

