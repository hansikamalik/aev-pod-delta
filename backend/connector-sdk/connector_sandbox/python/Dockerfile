# Packages the Python Connector SDK + the in-memory SampleConnector as a
# single, runnable image. No network access and no credentials are needed
# to prove the image works:
#
#   docker build -t connector-sdk-python .
#   docker run --rm connector-sdk-python
#
# should print a SUCCESS SyncResult and exit 0.
#
# This image is a *demonstration/verification* artifact, not a deployable
# service -- a real connector built on this SDK ships its own image that
# installs this package as a dependency and runs its own entrypoint.

FROM python:3.12-slim

# Keeps pip from writing .pyc caches / buffering stdout, standard for
# a small, short-lived container.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Only the packaging metadata first, so `pip install` is cached by Docker
# unless a dependency actually changes (source-only edits skip this layer).
COPY pyproject.toml ./
COPY connector_sdk ./connector_sdk

# Installs connector_sdk and its declared runtime dependencies only
# (pydantic, PyYAML, fastapi, uvicorn, httpx are declared in pyproject.toml
# for the whole sandbox; only pydantic is actually imported by connector_sdk
# itself -- the others belong to the mock server, not the SDK).
RUN pip install .
COPY connector_sandbox/python/scripts/run_sample.py ./scripts/run_sample.py


# Runs as a non-root user, standard container hygiene.
RUN useradd --create-home --uid 1000 sdk
USER sdk

ENTRYPOINT ["python", "scripts/run_sample.py"]
