# Docker Packaging (Week 4)

Packages both SDKs as standalone, runnable images so an external team can pull one image and confirm
the SDK works with a single command — no source checkout, no dependency install, no credentials, no
network. This is the Week 4 Connector SDK deliverable ("Docker Packaging for Both SDKs").

## What "package the SDK" means here

Each image runs **`SampleConnector`** — the in-memory fixture connector from Week 1 — through a full
`sync()`. It needs no mock server and no credentials, so it is the right thing to containerize on its
own: the image itself is the proof that the SDK works, not a demo of a specific vendor integration.

```
docker run --rm connector-sdk-python
docker run --rm connector-sdk-ts
```

Each should print a JSON `SyncResult` with `"status": "success"` and exit `0`. That is the entire
build-verification bar for this week.

```
{
  "connector": "sample",
  "status": "success",
  "assets_discovered": 3,
  "assets_pushed": 3,
  "errors": [],
  "started_at": "...",
  "finished_at": "..."
}
```

## File map

```
connector-sandbox/
├── docker-compose.yml       builds + tags both images
├── verify_docker.sh         build, run, assert SUCCESS (bash)
├── verify_docker.ps1        same, for Windows
├── python/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── scripts/run_sample.py     <- entrypoint
└── ts/
    ├── Dockerfile
    ├── .dockerignore
    ├── tsconfig.build.json       <- separate from the typecheck-only tsconfig.json
    └── src/scripts/runSample.ts  <- entrypoint (compiled by the build)
```

## Python image: single stage

```
FROM python:3.12-slim
COPY pyproject.toml, connector_sdk/
RUN pip install .
COPY scripts/run_sample.py
ENTRYPOINT ["python", "scripts/run_sample.py"]
```

One stage is enough: `connector_sdk` is pure Python, and its one direct dependency, `pydantic`, ships
precompiled wheels for `python:3.12-slim`, so nothing needs to be compiled from source. Runs as a
non-root user (`sdk`, uid 1000).

**Known tradeoff:** `pip install .` installs from the sandbox's root `pyproject.toml`, which declares
`fastapi`, `uvicorn` and `httpx` as dependencies too — those belong to the mock server and the reference
connector, not to `connector_sdk` itself, but `connector_sdk` isn't yet packaged separately. The image
works correctly; it is just heavier than a true SDK-only image would be. Splitting `connector_sdk` into
its own installable package (its own `pyproject.toml`, its own dependency list) is the real fix and is
tracked in [KNOWN_GAPS.md](KNOWN_GAPS.md) rather than done as a rushed change here, since the current
package layout is what every existing test imports against.

## TypeScript image: two stages

```
Stage 1 (build):   FROM node:22-slim
                    npm ci                       (full deps, incl. typescript)
                    npm run build                (tsc -p tsconfig.build.json -> dist/)

Stage 2 (runtime): FROM node:22-slim
                    npm ci --omit=dev            (zod only)
                    COPY --from=build /app/dist ./dist
                    ENTRYPOINT ["node", "dist/scripts/runSample.js"]
```

Two stages, because TypeScript must be compiled before Node can run it, but `typescript` and `vitest`
have no reason to be in the shipped image. `tsconfig.build.json` is separate from `tsconfig.json`
(the typecheck-only config used by `npm run typecheck` / CI) for two reasons:

- `tsconfig.json` sets `"noEmit": true` — it exists only to type-check, not to produce files.
- The build **excludes `src/testing/**`**. `contractHarness.ts` imports `vitest`, a devDependency;
  bundling it into the shipped image would either fail the build or ship test-only code to consumers.
  `src/index.ts` never re-exports anything from `testing/`, so nothing public is lost by excluding it.

Runs as a non-root user, same as the Python image.

## Build verification

```powershell
.\verify_docker.ps1          # Windows
./verify_docker.sh           # macOS / Linux / Git Bash
# or:
docker compose build --no-cache
```

Each script builds with `--no-cache` (so a stale layer can't hide a real problem), runs the image, and
checks **both** the exit code and the JSON body for `"status": "success"` — a container that builds and
exits 0 without actually running `sync()` correctly would still be a failure, and would slip past a
check that only looked at the exit code.

## What this does not cover

- **Not a deployable service.** These images demonstrate the SDK; they are not what a production
  connector ships. A real connector's own image installs one of these SDKs as a dependency and runs
  its own entrypoint.
- **Not an integration test.** Because it uses `SampleConnector`, this never touches the mock server,
  a real HTTP call, or any of the Week 1–3 scenario/failure work. Combining a containerized
  `ReferenceConnector` with a containerized mock server (via `docker-compose`, adding a `mock-server`
  service and pointing `ReferenceConnector`'s `base_url` at it) is a reasonable next step, but is not
  part of this week's scope and is not included here.
- **Not yet in CI.** `verify_docker.sh`/`.ps1` are meant to be run by hand this week, per the plan;
  wiring them into CI is future work.
