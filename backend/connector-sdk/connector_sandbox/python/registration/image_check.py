"""
Confirms an image reference is more than a plausible-looking string.

`ImageValidator` is the second seam. `FormatOnlySyntaxValidator` does the
cheap check (already covered by schemas.py's field_validator, really --
this exists as its own step so upgrading to the expensive check is a
one-class swap). The expensive version -- pull the image, run it with no
arguments the way our Week 4 SDK images do, confirm it exits 0 -- needs to
know where images actually live (a registry URL, auth for a private
registry) and whether the demo/CI environment is even allowed to pull
arbitrary images. Those are the open questions in
docs/REGISTRATION_READINESS.md, not something to guess at here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ImageCheckResult:
    ok: bool
    detail: str


class ImageValidator(Protocol):
    async def check(self, image: str) -> ImageCheckResult: ...


class FormatOnlySyntaxValidator:
    """Confirms the string looks like an image reference. Never pulls
    anything, never touches a network. This is what today's demo uses."""

    async def check(self, image: str) -> ImageCheckResult:
        if not image or " " in image:
            return ImageCheckResult(ok=False, detail="not a plausible image reference")
        return ImageCheckResult(ok=True, detail="syntax looks plausible (not pulled or run)")


# Sketch only -- not implemented, needs answers from docs/REGISTRATION_READINESS.md
# before it can be written for real.
#
# class PullAndRunValidator:
#     """Pulls the image and runs it with no arguments, expecting the same
#     contract our Week 4 SampleConnector images follow: exit 0, print a
#     JSON SyncResult. Needs: which registry, auth for private images,
#     whether the demo/CI host may pull arbitrary images at all."""
#     async def check(self, image: str) -> ImageCheckResult:
#         raise NotImplementedError
