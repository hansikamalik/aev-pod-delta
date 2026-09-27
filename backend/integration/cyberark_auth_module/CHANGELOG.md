---

## `CHANGELOG.md`
```markdown
# Changelog

All notable changes to the `cyberark_auth_module` project will be documented in this file.

## [1.0.0] - 2026-09-16

### Added
- Core `BaseAuthenticator` abstract class.
- `OAuth2Authenticator` with Client Credentials grant support for CyberArk Identity.
- `CCPClient` implementation for Central Credential Provider REST endpoints.
- `CyberArkAuthFactory` for dynamic authenticator instantiation.
- `ResilientSession` middleware with automated HTTP backoff retries.
- Comprehensive unit test suite with `requests-mock` fixtures.
