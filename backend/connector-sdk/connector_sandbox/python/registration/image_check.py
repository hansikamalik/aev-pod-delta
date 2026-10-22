"""
Image checks for POST /connectors/custom.

Two seams, both Protocols, so real infrastructure can replace the defaults
without touching the route:

  ImageValidator  decides whether an image *reference* is acceptable.
                  Default: PolicyImageValidator (strict syntax, registry
                  allowlist, pinned image). It never contacts the network.

  ImageScanner    decides whether an image is *safe to run* (vulnerability
                  scan, and later a sandbox run). Default: NotConfiguredScanner,
                  which reports "not_scanned". Nothing is scanned or sandboxed
                  today. See docs/REGISTRATION_SECURITY.md for what a real
                  implementation must do.

If you add code that pulls or inspects an image, it must follow the SSRF rules
in image_policy.resolve_public().
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .image_policy import ImagePolicy, ImagePolicyError, validate_image

import asyncio
import json
import os

SCAN_PASSED = "passed"
SCAN_FAILED = "failed"
SCAN_NOT_SCANNED = "not_scanned"


@dataclass
class ImageCheckResult:
    ok: bool
    detail: str


@dataclass
class ScanResult:
    status: str  # SCAN_PASSED | SCAN_FAILED | SCAN_NOT_SCANNED
    detail: str


class ImageValidator(Protocol):
    async def check(self, image: str) -> ImageCheckResult: ...


class ImageScanner(Protocol):
    async def scan(self, image: str) -> ScanResult: ...


class PolicyImageValidator:
    """Strict syntax + registry allowlist + pinning. Pulls, scans and runs nothing."""

    def __init__(self, policy: ImagePolicy) -> None:
        self._policy = policy

    async def check(self, image: str) -> ImageCheckResult:
        try:
            validate_image(image, self._policy)
        except ImagePolicyError as exc:
            return ImageCheckResult(ok=False, detail=f"{exc.code}: {exc.message}")
        return ImageCheckResult(ok=True, detail="reference is valid, registry is allowed, image is pinned (not pulled, scanned or run)")


class NotConfiguredScanner:
    """Placeholder until a real scanner exists. Anything other than "passed"
    must be treated by downstream code as NOT safe to run."""

    async def scan(self, image: str) -> ScanResult:
        return ScanResult(status=SCAN_NOT_SCANNED, detail="no image scanner is configured")


class TrivyDockerScanner:
    """Scan a registry image with Trivy running in a Docker container.

    HIGH or CRITICAL findings => failed.
    Scanner errors, timeouts or malformed reports => not_scanned.
    Only a completed scan with no findings at these severities => passed.
    """

    def __init__(
        self,
        docker_binary: str | None = None,
        trivy_image: str | None = None,
        timeout_seconds: int = 300,
    ) -> None:
        self.docker_binary = docker_binary or os.getenv("DOCKER_BINARY", "docker")
        self.trivy_image = trivy_image or os.getenv(
            "TRIVY_IMAGE", "aquasec/trivy:latest"
        )
        self.timeout_seconds = timeout_seconds

    async def scan(self, image: str) -> ScanResult:
        command = [
            self.docker_binary,
            "run",
            "--rm",
            "--pull=missing",
            self.trivy_image,
            "image",
            "--format", "json",
            "--scanners", "vuln",
            "--severity", "HIGH,CRITICAL",
            image,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )

        except FileNotFoundError:
            return ScanResult(
                status=SCAN_NOT_SCANNED,
                detail="Docker CLI is unavailable",
            )
        except asyncio.TimeoutError:
            return ScanResult(
                status=SCAN_NOT_SCANNED,
                detail="Trivy scan timed out",
            )
        except OSError:
            return ScanResult(
                status=SCAN_NOT_SCANNED,
                detail="Unable to start Trivy scan",
            )

        if process.returncode != 0:
            # Do not expose potentially sensitive raw stderr through the API.
            return ScanResult(
                status=SCAN_NOT_SCANNED,
                detail=f"Trivy exited with code {process.returncode}",
            )

        try:
            report = json.loads(stdout)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return ScanResult(
                status=SCAN_NOT_SCANNED,
                detail="Trivy returned an invalid JSON report",
            )

        if (
            not isinstance(report, dict)
            or not isinstance(report.get("ArtifactName"), str)
            or not report["ArtifactName"]
            or not isinstance(report.get("Results"), list)
        ):
            return ScanResult(
                status=SCAN_NOT_SCANNED,
                detail="Trivy report is incomplete",
            )

        findings = []
        for result in report["Results"]:
            if not isinstance(result, dict):
                return ScanResult(
                    status=SCAN_NOT_SCANNED,
                    detail="Trivy report contains an invalid result",
                )

            vulnerabilities = result.get("Vulnerabilities") or []
            if not isinstance(vulnerabilities, list):
                return ScanResult(
                    status=SCAN_NOT_SCANNED,
                    detail="Trivy report contains invalid vulnerability data",
                )

            for vulnerability in vulnerabilities:
                if not isinstance(vulnerability, dict):
                    return ScanResult(
                        status=SCAN_NOT_SCANNED,
                        detail="Trivy report contains an invalid vulnerability",
                    )

                if vulnerability.get("Severity") in {"HIGH", "CRITICAL"}:
                    findings.append(vulnerability.get("VulnerabilityID", "unknown"))

        if findings:
            examples = ", ".join(findings[:5])
            return ScanResult(
                status=SCAN_FAILED,
                detail=f"Found {len(findings)} HIGH/CRITICAL vulnerabilities: {examples}",
            )

        return ScanResult(
            status=SCAN_PASSED,
            detail="Trivy completed; no HIGH/CRITICAL vulnerabilities found",
        )

class FormatOnlySyntaxValidator:
    """UNSAFE, do not use for registration. Kept only so old imports still work.

    It accepts URLs, metadata-service addresses, file:// paths, localhost and
    shell metacharacters; it only rejects empty strings and whitespace.
    """

    async def check(self, image: str) -> ImageCheckResult:
        if not image or " " in image:
            return ImageCheckResult(ok=False, detail="not a plausible image reference")
        return ImageCheckResult(ok=True, detail="syntax looks plausible (UNSAFE check: not for registration)")
