# Registration Endpoint: Security

Applies to `POST /connectors/custom` (`python/registration/`). Read this with
[REGISTRATION_READINESS.md](REGISTRATION_READINESS.md) and [KNOWN_GAPS.md](KNOWN_GAPS.md).

## Status at a glance

| Control | Status |
|---|---|
| Strict image reference syntax | **Enforced** |
| Registry allowlist (default deny) | **Enforced** |
| Pinned images (digest, or a tag other than `latest`) | **Enforced** |
| SSRF: no fetching from the endpoint | **Not applicable yet**: nothing contacts the network |
| SSRF: safe-resolution rules for a future fetcher | Written and tested (`resolve_public`), **not yet used** |
| Schema content validation and size limits | **Enforced** |
| Unknown request fields rejected | **Enforced** |
| Secrets rejected from `config_schema` | **Enforced** |
| Image scanning | **Not implemented.** Interface only; every record reports `scan_status: "not_scanned"` |
| Sandboxing | **Not implemented.** Requirements below |
| Authentication / authorization | **Not implemented** |
| Rate limiting, request-size limit | **Not implemented** |
| Persistence, audit log | **Not implemented** (in-memory store) |

A registered connector is **not** vetted. Downstream code must treat anything whose `scan_status` is not
`passed` as unsafe to run.

## What the endpoint accepts, and why that is a risk

The caller supplies an image reference and two schemas. Without checks, the reference can point the
platform at a registry the caller controls (so the platform later runs attacker code), or at an internal
address (SSRF) if anything ever fetches it. The earlier check accepted all of the following:
`http://169.254.169.254/latest/meta-data` (the cloud metadata address), `file:///etc/passwd`,
`http://localhost:8080/evil`, `127.0.0.1:5000/evil:latest`, `user:pass@registry.example.com/x:1`,
`registry.example.com/x:1;rm-rf-/`, `$(whoami)/x`, and any public registry.

## Controls in force

### 1. Image reference syntax (`image_policy.parse_image_ref`)

The grammar is `registry[:port]/repository[:tag][@sha256:<64 hex>]`. Everything else is rejected with a
stable error code.

| Rejected | Code |
|---|---|
| Empty, non-string, over 255 characters | `empty`, `too_long` |
| Whitespace, control or non-ASCII characters (including look-alike letters) | `bad_characters` |
| Any URL scheme (`http://`, `file://`) | `scheme_not_allowed` |
| `user:pass@host`, malformed digests | `bad_digest` |
| No explicit registry host (Docker-Hub-style `library/alpine`) | `registry_required`, `bad_registry_host` |
| IP addresses as the registry, in any form (`127.0.0.1`, `0x7f.0.0.1`, `[::1]`) | `ip_literal_host` |
| `localhost`, single-label hosts, decimal-integer IPs | `bad_registry_host` |
| Bad ports | `bad_registry_port` |
| Shell metacharacters, `..`, empty path segments, uppercase, more than 8 segments | `bad_repository` |
| Bad tags | `bad_tag` |

### 2. Registry allowlist and pinning (`ImagePolicy`)

Set `ALLOWED_REGISTRIES` to a comma-separated list of hosts, for example
`registry.example.com,ghcr.io`.

- **Default deny.** If the variable is unset or empty, every registration is rejected
  (`no_registries_configured`).
- Matching is **exact** on `host` or `host:port`, case-insensitive. There are no wildcards, and a
  sub-domain or look-alike (`registry.example.com.evil.io`) does not match.
- **Pinned only.** The image must carry a `sha256` digest, or an explicit tag that is not `latest`
  (`unpinned_image`). A tag can be moved after registration; a digest cannot. If you want to *require*
  digests, set `require_pinned` and tighten `ImagePolicy.check`.

### 3. Schema validation (`schema_rules.check_envelope`)

`type` must be `"object"`; every property must be an object with a valid JSON `type`; `required` may only
name defined properties; `secret` must be a boolean; property names are limited to letters, digits and
underscores; at most 50 properties and 16 KB. Unknown top-level request fields and unknown envelope keys
are rejected, so a flat field map cannot be silently stored as an empty schema.

A property marked `secret: true` inside `config_schema` is rejected: configuration is stored and displayed
as plain settings. Non-secret credentials (a username, an email) are allowed in `credential_schema`.

## SSRF

Today the endpoint **never contacts the network**: it parses a string and stores it. So there is no live
SSRF exposure. The risk begins the moment anything resolves or fetches a registry host (a pull, a digest
lookup, a scan). `resolve_public()` and `is_public_address()` define the rules that code must follow:

1. Only contact hosts that passed the allowlist.
2. Resolve DNS **once**, in your code, and require that **every** returned address is public. Refuse
   loopback, private, link-local (including `169.254.169.254`), carrier-grade (`100.64/10`), unspecified,
   multicast and reserved ranges, and IPv6 forms that embed an IPv4 address (IPv4-mapped, 6to4, Teredo,
   NAT64).
3. **Connect to the resolved IP**, sending the hostname only as TLS SNI / `Host`. Do not resolve again
   (that is how DNS rebinding works).
4. Do not follow redirects to a different host. Set connect and read timeouts. Cap the response size.

## Not implemented: image scanning and sandboxing

These need infrastructure and an owner; the endpoint only provides the seam.

**What exists:** `ImageScanner` (interface), `NotConfiguredScanner` (returns `not_scanned`), a
`scan_status` field on every record, and a route that rejects a `failed` scan with a 422.

**What a real scanner must do:**
- Resolve the tag to a digest and store the digest, so what was scanned is what runs.
- Scan for known vulnerabilities and secrets baked into the image, and block on a defined severity.
- Re-scan on a schedule, since new vulnerabilities are published after registration.
- Follow the SSRF rules above when it contacts the registry.

**What a real sandbox must do** (before registered images run anywhere that matters):
- Run as a non-root user, with a read-only root filesystem and all Linux capabilities dropped.
- No network by default; egress only to the vendor host the connector is configured for.
- Hard CPU, memory, process and time limits.
- Inject credentials at runtime only, never bake them into the image or pass them through registration.
- Prefer a stronger isolation boundary than a plain container for untrusted code (a user-space kernel or
  a micro-VM), and a seccomp profile otherwise.

Until those exist, say so plainly: registration succeeds, but the connector is **unvetted**.

## Not implemented: authentication, limits, persistence

Nothing identifies who is registering a connector, limits how often, or caps the request body. The store is
in memory. These are tracked as gaps 14 and 15 in [KNOWN_GAPS.md](KNOWN_GAPS.md).

## Decisions needed

| # | Decision | Default in the code |
|---|---|---|
| 1 | Who owns and maintains the registry allowlist? | Environment variable, deny all if unset |
| 2 | Require digests, or accept explicit tags? | Digest or explicit non-`latest` tag |
| 3 | Where do scanning and sandboxing live, and who owns them? | Nowhere yet |
| 4 | Who may register a connector? | Anyone who can reach the endpoint |
| 5 | May a registered image be run before `scan_status` is `passed`? | The code does not run anything; downstream must decide, and should say no |

## Verification status

- `test_image_policy.py` (93 cases) and `test_schema_rules.py` (17 cases) cover the logic above, including
  a seeded fuzz of the parser. They ran green, and were mutation-checked: removing the allowlist, URL,
  pinning, link-local, first-answer-only DNS, required-subset and property-type rules each makes tests
  fail. Removing only the IP-literal branch does not, because a second rule in the parser rejects the same
  inputs with the same code; that overlap is deliberate.
- `test_registration.py` (21 test functions) covers the same rules through HTTP, plus scan status via
  dependency overrides. **It has not been run**: it needs FastAPI and pydantic, which were unavailable where
  it was written. Its 42 payload expectations were replayed through the real policy and schema modules and
  all match, but the HTTP wiring (`schemas.py`, `app.py`) is checked only by compilation and reading.
  Run `pytest tests/ -v` before relying on it.
