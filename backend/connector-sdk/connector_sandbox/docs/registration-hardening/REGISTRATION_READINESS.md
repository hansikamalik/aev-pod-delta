# Registration Endpoint: Readiness Notes

For `POST /connectors/custom` (Week 3, Connector SDK). Code: `python/registration/`.
Run the demo: `pytest tests/test_registration.py -v`, or `uvicorn registration.app:app --port 8081`.

## Why it's built this way

You don't have specs from the modules this depends on yet (where images live, how credentials get
stored, what auth context a request carries). Rather than guess and bake those guesses into the route
logic, every unknown is pushed behind one of two interfaces, and today's demo uses the cheapest possible
stub behind each:

```
                      ┌─────────────────────────────┐
  POST/GET requests → │  registration/app.py (route)│
                      └──────────────┬──────────────┘
                                     │ depends on two Protocols only
                 ┌───────────────────┼───────────────────┐
                 ▼                                       ▼
     ConnectorRegistry (registry.py)          ImageValidator (image_check.py)
     ── today: InMemoryConnectorRegistry      ── today: PolicyImageValidator
     ── later: swap in the real store         ── later: swap in a real pull-and-run check
```

The route (`app.py`) never imports a concrete registry or validator directly — only the `Depends(...)`
factories do, and those are the only two lines you'll touch when the real infra shows up. This is the
same seam-isolation pattern the Docker packaging doc uses for "what to swap later" — same idea, applied
one layer up.

## What's already decided, and why

- **Request shape reuses the SDK's own schema envelope** (`{type, properties, required}`), the same
  thing `describe_config()`/`describe_credentials()` already return. Not a new format invented for this
  endpoint — see `docs/DOCKER.md`'s note on the flat-map-vs-envelope bug we already found once in the TS
  guide. `test_flat_field_map_config_schema_is_rejected` in the demo suite is there specifically so that
  bug can't come back silently.
- **`name` reuses the naming rule** connector_sdk already enforces (`^[a-z][a-z0-9_]*$`), not a second
  regex invented here.
- **Secrets belong in `credential_schema`, not `config_schema`.** A field marked `"secret": true` inside
  `config_schema` is rejected. (An earlier rule required every credential field to be secret; it rejected
  the repo's own Jira connector, whose `email` is a credential but not a secret, so it was replaced.)
- **Image validation is policy-based, but offline.** The reference must parse strictly, its registry must be
  on the `ALLOWED_REGISTRIES` allowlist (default deny), and it must be pinned (a digest, or a tag other
  than `latest`). Nothing pulls, scans or runs the image, so a broken or malicious image from an allowed
  registry is still not caught. See [REGISTRATION_SECURITY.md](REGISTRATION_SECURITY.md).
- **Duplicate names are rejected (409), not overwritten.** Worth confirming this is what you actually
  want once Abhiram is re-registering during the Week 5 dogfood test — a reject-on-duplicate policy will
  make his normal "tweak and re-run" loop annoying. Might want `PUT` (upsert) instead of, or alongside,
  this `POST`.

## Questions to bring to the other squads, in the order they'll actually block you

1. **Where do images live, and how does this endpoint (or something downstream of it) actually verify
   one exists?** A public registry, a private one with its own auth, or something the platform builds
   and hosts itself all lead to different validators. Until you know this, the offline
   `PolicyImageValidator` (syntax, allowlist, pinning) is the honest ceiling of what you can build.
2. **Does registering a connector mean anything runs immediately**, even a cheap sanity pull-and-run
   (the same "exit 0, print a `SyncResult`" contract our Week 4 SDK images already satisfy), or is
   registration purely metadata and correctness is discovered later? This is the single biggest
   difference between "registration is fast and dumb" and "registration is slow and actually protects
   the dogfood test from a broken image."
3. **What does the real registry/storage layer look like** — a database, another team's service with
   its own API, something else? Only changes `registry.py`; nothing else moves.
4. **What auth/RBAC context does a request to this endpoint carry?** Right now there's no notion of
   "who is registering this" or "are they allowed to." If registration should be scoped per-user or
   per-team, that's a request-shape and route-dependency change, so better to know before Week 5 than
   during it.
5. **Does the credential schema submitted here need to match Vault's actual secret-storage shape**, or
   is this purely a UI/validation-time schema, decoupled from how credentials get stored at runtime?
6. **Versioning and overwrite policy** — confirmed reject-on-duplicate is really what's wanted (see
   above), or should re-registration be allowed, or version-tagged?

## What "ready" looks like once those answers arrive

- Write a new class implementing `ConnectorRegistry` in `registry.py` (or a new file), point
  `get_registry()` in `app.py` at it. The route and every existing test in `test_registration.py`
  keep working unchanged, because they only ever talked to the Protocol.
- Same for `ImageValidator` — the commented-out `PullAndRunValidator` sketch in `image_check.py` is the
  shape of the real thing once question 1 and 2 are answered.
- If an auth context is added, it's a new `Depends(...)` parameter on the route functions plus a
  permission check — additive, doesn't require restructuring what's already here.

## Demo script (works today, no other team's infra needed)

```bash
cd python
uvicorn registration.app:app --port 8081
```

```bash
curl -X POST http://127.0.0.1:8081/connectors/custom -H "Content-Type: application/json" -d '{
  "name": "my_connector",
  "image": "registry.example.com/my-connector:1.0.0",
  "config_schema": {"type": "object", "properties": {"base_url": {"type": "string"}}, "required": ["base_url"]},
  "credential_schema": {"type": "object", "properties": {"api_key": {"type": "string", "secret": true}}, "required": ["api_key"]}
}'
curl http://127.0.0.1:8081/connectors/custom
curl http://127.0.0.1:8081/connectors/custom/my_connector
```
