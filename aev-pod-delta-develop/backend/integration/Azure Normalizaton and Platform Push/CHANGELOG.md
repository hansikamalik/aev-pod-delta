#Version History & Changes

#### **`CHANGELOG.md`**
```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-09-15

### Added
- Created concrete normalizer classes for Azure Virtual Machines, Storage Accounts, Entra ID Users, SQL Databases, and Function Apps.
- Integrated Draft-07 JSON Schema validation against `contracts/azure_cam_schema.json`.
- Implemented `PlatformPushEngine` featuring configurable retry thresholds and HTTP status code filtering.
- Implemented `DLQHandler` for persisting invalid payloads and HTTP error dumps.
- Included end-to-end integration test suite and coverage reporting via `./run_tests.sh`.
