"""Microsoft Entra ID connector — Week 1: auth module only.

Abhiram's Week 1 deliverable (auth module, built solo Thu–Fri after shadowing
Harshal on Sentinel Mon–Wed). Full connector — discovery, normalization,
push — lands in Week 2.
"""
from .auth import EntraIDAuth

__all__ = ["EntraIDAuth"]
