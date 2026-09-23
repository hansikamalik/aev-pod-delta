"""
Stand-in for the shared Connector ABC.

The Connector SDK squad owns the canonical version of this interface
(6 methods, mirrored in the TypeScript SDK — see the Pod Delta plan, Week 1
Connector SDK section: "Abstract Connector class - same 6 methods as the
Python ABC"). This local copy exists so this repo runs standalone; swap the
import below for the real one once confirmed:

    from connector_sdk.base import Connector
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List


class Connector(ABC):
    """Base interface every AEV Platform connector implements."""

    @abstractmethod
    def authenticate(self) -> None:
        """Acquire and cache whatever credential/token this connector needs."""

    @abstractmethod
    def discover(self) -> Iterable[Dict[str, Any]]:
        """Enumerate raw objects from the source system."""

    @abstractmethod
    def ingest(self, raw_objects: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Pull/shape the full record for each discovered object."""

    @abstractmethod
    def normalize(self, ingested_objects: Iterable[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """Map ingested objects to the shared Asset/Finding shape(s)."""

    @abstractmethod
    def push(self, normalized: Dict[str, List[Any]]) -> Dict[str, Any]:
        """Send normalized assets/findings to the platform's asset/exposure service."""

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Report whether this connector can currently reach its dependencies."""
