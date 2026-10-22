# Custom connector registration: handover status

## What this implementation enforces
- Default-deny registry allowlist (`ALLOWED_REGISTRIES` must be configured).
- Strict image-reference parsing; rejects URL schemes, IP literals, disallowed registries, mutable `latest`/untagged references, and invalid tag/digest forms.
- Schema envelope and nested schema checks, required-property consistency, bounded schema complexity, and config-vs-credential secret separation.
- Credential schema fields must explicitly declare `secret: true`.
- Duplicate connector names return HTTP 409.
- The image validator does not fetch/pull arbitrary URLs, avoiding registration-time SSRF.
- The default scanner explicitly returns `not_scanned`; the API must not claim the image is scanned or safe to execute.

## Important limitations (do not call this production-ready)
- The registry is process-local/in-memory; records disappear on restart and are not shared across workers.
- Authentication/authorization and rate limiting must be supplied by the platform gateway before exposing this API to other users or networks.
- Request-body limits should be enforced at the reverse proxy/server boundary.
- Image vulnerability scanning and runtime sandboxing are not implemented by the default scanner. A real scanner integration must fail closed before execution, and connector execution must run in a restricted container (non-root, read-only filesystem, no Docker socket, restricted network/CPU/memory/PIDs, secrets mounted only at runtime).
- The SSRF policy protects the registration endpoint by not fetching images. If a later implementation pulls or inspects images itself, it must validate registry DNS/IP resolution, block private/link-local/loopback/multicast/reserved addresses, disable redirects or revalidate every redirect, impose strict timeouts/size limits, and prevent DNS rebinding.
- An `image_check_status` of `ok` means reference policy validation only, not existence or trust. `scan_status=not_scanned` is not approval to run the image.

## Verification required on a clean clone
1. Run Python registration tests and the complete Python sandbox suite.
2. Run TypeScript sandbox and canonical SDK test/build/lint commands.
3. Run `verify_docker.ps1` on Windows with Docker Desktop running (or `verify_docker.sh`).
4. Complete a real dogfood run using public docs only, record friction, then write the guide.
5. Do not mark the M4 SDK acceptance criterion complete until both Docker images build/run and an external tester registers and syncs a working custom connector.
