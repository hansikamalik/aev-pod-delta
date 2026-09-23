"""Testing utilities for connector development.

Requires pytest: ``pip install connector-sdk[test]``.
"""

from .doubles import (
    FailingConnector,
    FakeConnector,
    InMemoryPlatformClient,
    sample_resources,
)

__all__ = [
    "ConnectorContractTests",
    "run_sync",
    "FakeConnector",
    "FailingConnector",
    "InMemoryPlatformClient",
    "sample_resources",
]


def __getattr__(name: str):
    """Lazily import ConnectorContractTests/run_sync, which need pytest.

    Keeps FakeConnector/InMemoryPlatformClient usable (e.g. from the CLI or
    application code) in environments without pytest installed.
    """
    if name in {"ConnectorContractTests", "run_sync"}:
        from . import contract

        return getattr(contract, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
