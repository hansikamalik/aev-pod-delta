"""
Image reference parsing and policy for POST /connectors/custom.

Standard library only, so it can be tested without FastAPI or pydantic.

Why this exists: the endpoint accepts an image reference from the caller. The
old check ("not empty, no spaces, at most two colons") accepted metadata-service
URLs, file:// URLs, localhost, shell metacharacters and any public registry.
This module enforces three things instead:

1. SYNTAX    parse_image_ref(): a strict `registry[:port]/repo[:tag][@sha256:...]`
             grammar. Anything else (schemes, user:pass@, IP addresses, whitespace,
             shell characters, path traversal) is rejected.
2. POLICY    ImagePolicy: the registry must be on an explicit allowlist
             (default deny), and the image must be pinned (a digest, or an explicit
             tag other than "latest").
3. SSRF      is_public_address() / resolve_public(): rules for the *future* code
             that actually contacts a registry. Nothing in the registration
             endpoint contacts the network today, so SSRF is not exploitable yet.
             These helpers exist so that whoever adds a pull-and-run check has the
             safe behaviour ready (and tested) instead of improvising it.
"""
from __future__ import annotations

import ipaddress
import os
import re
import socket
from dataclasses import dataclass
from typing import Callable, Mapping

MAX_REF_LENGTH = 255
MAX_REPO_DEPTH = 8

_DNS_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_HOST_RE = re.compile(rf"^{_DNS_LABEL}(?:\.{_DNS_LABEL})+$")  # needs a dot: rejects "localhost"
_PORT_RE = re.compile(r"^[0-9]{1,5}$")
_REPO_COMPONENT_RE = re.compile(r"^[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*$")
_TAG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$")
_DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")


class ImagePolicyError(ValueError):
    """A rejected image reference. `code` is stable and safe to match in tests and logs."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ImageRef:
    registry: str            # lowercase host[:port]
    repository: str          # path inside the registry, e.g. "team/jira"
    tag: str | None = None
    digest: str | None = None

    @property
    def name(self) -> str:
        return f"{self.registry}/{self.repository}"


# ---- 1. syntax -----------------------------------------------------------

def parse_image_ref(ref: object) -> ImageRef:
    """Parse a reference, or raise ImagePolicyError. Never raises anything else."""
    if not isinstance(ref, str) or not ref:
        raise ImagePolicyError("empty", "image reference is empty")
    if len(ref) > MAX_REF_LENGTH:
        raise ImagePolicyError("too_long", f"image reference is longer than {MAX_REF_LENGTH} characters")
    if not ref.isascii() or any(ord(c) <= 32 or ord(c) == 127 for c in ref):
        raise ImagePolicyError("bad_characters", "image reference must be printable ASCII with no whitespace")
    if "://" in ref:
        raise ImagePolicyError("scheme_not_allowed", "image reference must not be a URL (no scheme such as http:// or file://)")

    name, digest = ref, None
    if "@" in ref:
        name, _, digest = ref.partition("@")
        if not _DIGEST_RE.match(digest):
            raise ImagePolicyError(
                "bad_digest",
                "'@' is only allowed before a sha256 digest; credentials in the reference (user:password@host) are not allowed",
            )

    registry_part, slash, rest = name.partition("/")
    if not slash or not rest:
        raise ImagePolicyError("registry_required", "image reference must start with an explicit registry host (registry.example.com/repo:tag)")

    registry = _parse_registry(registry_part)

    tag = None
    colon, last_slash = rest.rfind(":"), rest.rfind("/")
    if colon > last_slash:
        rest, tag = rest[:colon], rest[colon + 1:]
        if not _TAG_RE.match(tag):
            raise ImagePolicyError("bad_tag", f"invalid tag {tag!r}")

    components = rest.split("/")
    if not 1 <= len(components) <= MAX_REPO_DEPTH or not all(_REPO_COMPONENT_RE.match(c) for c in components):
        raise ImagePolicyError("bad_repository", f"invalid repository path {rest!r} (lowercase letters, digits, '.', '_', '-' and '/' only)")

    return ImageRef(registry=registry, repository=rest, tag=tag, digest=digest)


def _parse_registry(part: str) -> str:
    if part.startswith("["):
        raise ImagePolicyError("ip_literal_host", "registry must be a DNS name, not an IP address")
    host, colon, port = part.partition(":")
    host = host.lower()
    if colon:
        if not _PORT_RE.match(port) or not 0 < int(port) <= 65535:
            raise ImagePolicyError("bad_registry_port", f"invalid registry port {port!r}")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ImagePolicyError("ip_literal_host", "registry must be a DNS name, not an IP address")
    if not _HOST_RE.match(host):
        raise ImagePolicyError("bad_registry_host", f"invalid registry host {host!r} (a full DNS name is required; 'localhost' and single-label names are not allowed)")
    if not re.search(r"[a-z]", host.rsplit(".", 1)[1]):
        raise ImagePolicyError("ip_literal_host", "registry looks like an IP address")
    return f"{host}:{port}" if colon else host


# ---- 2. policy -----------------------------------------------------------

@dataclass(frozen=True)
class ImagePolicy:
    """Which registries are allowed, and whether images must be pinned.

    allowed_registries: exact `host` or `host:port` entries, lowercase, no wildcards.
    An empty allowlist denies everything (default deny).
    """

    allowed_registries: frozenset[str] = frozenset()
    require_pinned: bool = True   # a digest, or an explicit tag that is not "latest"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, var: str = "ALLOWED_REGISTRIES") -> "ImagePolicy":
        raw = (os.environ if env is None else env).get(var, "")
        return cls(allowed_registries=frozenset(x.strip().lower() for x in raw.split(",") if x.strip()))

    def check(self, ref: ImageRef) -> None:
        if not self.allowed_registries:
            raise ImagePolicyError("no_registries_configured", "no image registries are allowed: set ALLOWED_REGISTRIES (default deny)")
        if ref.registry not in self.allowed_registries:
            raise ImagePolicyError("registry_not_allowed", f"registry {ref.registry!r} is not on the allowlist")
        if self.require_pinned and ref.digest is None and ref.tag in (None, "latest"):
            raise ImagePolicyError("unpinned_image", "image must be pinned: use a digest (@sha256:...) or an explicit tag other than 'latest'")


def validate_image(ref: object, policy: ImagePolicy) -> ImageRef:
    parsed = parse_image_ref(ref)
    policy.check(parsed)
    return parsed


# ---- 3. SSRF rules for any future code that contacts a registry ------------

_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def is_public_address(ip: str) -> bool:
    """True only for globally routable unicast addresses.

    Rejects loopback, private, link-local (including the 169.254.169.254 cloud
    metadata address), shared/carrier-grade (100.64/10), unspecified, reserved,
    multicast, and IPv6 forms that can smuggle an IPv4 address (IPv4-mapped,
    6to4, Teredo, NAT64).
    """
    addr = ipaddress.ip_address(ip)
    if addr.version == 6:
        if addr.ipv4_mapped is not None:
            addr = addr.ipv4_mapped
        elif addr.sixtofour is not None or addr.teredo is not None or addr in _NAT64:
            return False
    return addr.is_global and not addr.is_multicast


def resolve_public(
    host: str,
    port: int = 443,
    resolver: Callable[..., list] = socket.getaddrinfo,
) -> list[str]:
    """Resolve `host` and return its addresses, but only if EVERY one is public.

    Rules for the caller (the future pull/scan code):
      * connect to one of the returned IPs directly (send the original hostname
        only as TLS SNI / Host header). Do not resolve again: a second lookup is
        how DNS-rebinding attacks work;
      * do not follow redirects to a different host;
      * set connect and read timeouts, and cap the response size.
    `resolver` is injectable so this is testable without a network.
    """
    infos = resolver(host, port, type=socket.SOCK_STREAM)
    ips = sorted({info[4][0] for info in infos})
    if not ips:
        raise ImagePolicyError("unresolvable", f"{host!r} did not resolve to any address")
    bad = [ip for ip in ips if not is_public_address(ip)]
    if bad:
        raise ImagePolicyError("non_public_address", f"{host!r} resolves to non-public address(es): {bad}")
    return ips
