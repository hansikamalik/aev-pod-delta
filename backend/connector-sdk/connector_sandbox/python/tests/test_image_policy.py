"""
Tests for registration/image_policy.py: reference syntax, registry allowlist,
pinning, and the SSRF address rules. No FastAPI or pydantic needed.

    pytest tests/test_image_policy.py -v
"""
from __future__ import annotations

import random
import re
import socket

import pytest

from registration.image_policy import (
    ImagePolicy,
    ImagePolicyError,
    is_public_address,
    parse_image_ref,
    resolve_public,
    validate_image,
)

DIGEST = "sha256:" + "a" * 64
ALLOWED = ImagePolicy(allowed_registries=frozenset({"registry.example.com"}))


def code_of(fn, *args):
    with pytest.raises(ImagePolicyError) as err:
        fn(*args)
    return err.value.code


# ---- syntax ------------------------------------------------------------

@pytest.mark.parametrize(
    "ref,registry,repository,tag,digest",
    [
        ("registry.example.com/team/jira:0.1.0", "registry.example.com", "team/jira", "0.1.0", None),
        ("registry.example.com/jira:1", "registry.example.com", "jira", "1", None),
        (f"registry.example.com/team/jira@{DIGEST}", "registry.example.com", "team/jira", None, DIGEST),
        (f"registry.example.com/team/jira:1.2@{DIGEST}", "registry.example.com", "team/jira", "1.2", DIGEST),
        ("registry.example.com:5000/team/jira:1", "registry.example.com:5000", "team/jira", "1", None),
        ("Registry.Example.COM/team/jira:1", "registry.example.com", "team/jira", "1", None),
        ("ghcr.io/org/my-image_v2.x:v1.0.0-rc1", "ghcr.io", "org/my-image_v2.x", "v1.0.0-rc1", None),
    ],
)
def test_valid_references_parse(ref, registry, repository, tag, digest):
    parsed = parse_image_ref(ref)
    assert (parsed.registry, parsed.repository, parsed.tag, parsed.digest) == (registry, repository, tag, digest)


@pytest.mark.parametrize(
    "ref,code",
    [
        ("", "empty"),
        (None, "empty"),
        (123, "empty"),
        ("a" * 300, "too_long"),
        # URLs and schemes
        ("http://169.254.169.254/latest/meta-data", "scheme_not_allowed"),
        ("http://localhost:8080/evil", "scheme_not_allowed"),
        ("file:///etc/passwd", "scheme_not_allowed"),
        ("https://registry.example.com/team/jira:1", "scheme_not_allowed"),
        # IP addresses and look-alikes as the registry
        ("127.0.0.1:5000/evil:1", "ip_literal_host"),
        ("10.0.0.5/internal/img:1", "ip_literal_host"),
        ("169.254.169.254/x:1", "ip_literal_host"),
        ("0x7f.0.0.1/evil:1", "ip_literal_host"),
        ("[::1]:5000/evil:1", "ip_literal_host"),
        ("2130706433/evil:1", "bad_registry_host"),      # decimal form of 127.0.0.1
        ("localhost/evil:1", "bad_registry_host"),
        ("localhost:5000/evil:1", "bad_registry_host"),
        ("library/alpine:3.20", "bad_registry_host"),    # Docker-Hub style, no explicit registry
        ("alpine", "registry_required"),
        ("registry.example.com/", "registry_required"),
        ("registry.example.com:99999/x:1", "bad_registry_port"),
        ("registry.example.com:abc/x:1", "bad_registry_port"),
        # credentials, digests
        ("user:pass@registry.example.com/x:1", "bad_digest"),
        ("registry.example.com/x@sha256:short", "bad_digest"),
        ("registry.example.com/x@md5:" + "a" * 32, "bad_digest"),
        # whitespace, control and non-ASCII characters
        ("registry.example.com/x:1 ", "bad_characters"),
        ("registry.example.com/x:1\nHost: evil", "bad_characters"),
        ("registry.example.com/x:1\x00", "bad_characters"),
        ("reg\u0456stry.example.com/x:1", "bad_characters"),   # Cyrillic i
        # shell metacharacters and traversal in the repository
        ("registry.example.com/x:1;rm-rf-/", "bad_repository"),
        ("registry.example.com/$(whoami):1", "bad_repository"),
        ("registry.example.com/`id`:1", "bad_repository"),
        ("registry.example.com/../../etc/passwd:1", "bad_repository"),
        ("registry.example.com//x:1", "bad_repository"),
        ("registry.example.com/UPPER/case:1", "bad_repository"),
        ("registry.example.com/" + "/".join(["a"] * 9) + ":1", "bad_repository"),
        # tags
        ("registry.example.com/x:", "bad_tag"),
        ("registry.example.com/x:-leading", "bad_tag"),
        ("registry.example.com/x:" + "t" * 129, "bad_tag"),
        ("registry.example.com/x:a:b", "bad_repository"),  # last colon is the tag; "x:a" is not a valid repository
    ],
)
def test_bad_references_are_rejected_with_a_stable_code(ref, code):
    assert code_of(parse_image_ref, ref) == code


def test_parser_never_raises_anything_but_imagepolicyerror():
    """Seeded fuzz: random strings built from the characters that matter."""
    rng = random.Random(1234)
    alphabet = "abcXYZ019.-_:/@[]()$;`'\"\\ \t\n%&?#=+~*!<>,\u0456\u00e9"
    safe = re.compile(r"^[A-Za-z0-9._:/@-]+$")
    for _ in range(5000):
        ref = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))
        try:
            parsed = parse_image_ref(ref)
        except ImagePolicyError:
            continue
        # anything accepted must contain only the safe characters
        assert safe.match(ref), f"accepted unsafe reference {ref!r}"
        assert " " not in parsed.registry and "/" not in parsed.registry


# ---- policy -------------------------------------------------------------

def test_default_deny_when_no_registries_are_configured():
    assert code_of(validate_image, "registry.example.com/x:1", ImagePolicy()) == "no_registries_configured"


def test_registry_must_be_on_the_allowlist():
    assert validate_image("registry.example.com/team/jira:1", ALLOWED).registry == "registry.example.com"
    assert code_of(validate_image, "evil.example.com/malware:1", ALLOWED) == "registry_not_allowed"


def test_allowlist_is_exact_and_port_sensitive():
    with_port = ImagePolicy(allowed_registries=frozenset({"registry.example.com:5000"}))
    assert validate_image("registry.example.com:5000/x:1", with_port)
    assert code_of(validate_image, "registry.example.com/x:1", with_port) == "registry_not_allowed"
    assert code_of(validate_image, "registry.example.com:5001/x:1", with_port) == "registry_not_allowed"
    # a sub-domain is not the allowed domain, and there are no wildcards
    assert code_of(validate_image, "evil.registry.example.com/x:1", ALLOWED) == "registry_not_allowed"
    assert code_of(validate_image, "registry.example.com.evil.io/x:1", ALLOWED) == "registry_not_allowed"


def test_host_comparison_ignores_case():
    assert validate_image("REGISTRY.EXAMPLE.COM/x:1", ALLOWED).registry == "registry.example.com"


@pytest.mark.parametrize("ref", ["registry.example.com/x", "registry.example.com/x:latest"])
def test_unpinned_images_are_rejected(ref):
    assert code_of(validate_image, ref, ALLOWED) == "unpinned_image"


def test_digest_or_explicit_tag_counts_as_pinned():
    assert validate_image(f"registry.example.com/x@{DIGEST}", ALLOWED).digest == DIGEST
    assert validate_image("registry.example.com/x:2.0", ALLOWED).tag == "2.0"


def test_pinning_can_be_switched_off():
    relaxed = ImagePolicy(allowed_registries=frozenset({"registry.example.com"}), require_pinned=False)
    assert validate_image("registry.example.com/x", relaxed)


def test_from_env_parses_and_normalises_the_allowlist():
    policy = ImagePolicy.from_env({"ALLOWED_REGISTRIES": " Registry.Example.com , ghcr.io,, "})
    assert policy.allowed_registries == frozenset({"registry.example.com", "ghcr.io"})


def test_from_env_with_nothing_set_denies_everything():
    assert ImagePolicy.from_env({}).allowed_registries == frozenset()


def test_wildcard_entries_match_nothing():
    star = ImagePolicy(allowed_registries=frozenset({"*", "*.example.com"}))
    assert code_of(validate_image, "registry.example.com/x:1", star) == "registry_not_allowed"


# ---- SSRF address rules ------------------------------------------------------

@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34", "2606:4700:4700::1111"])
def test_public_addresses_are_allowed(ip):
    assert is_public_address(ip) is True


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1", "127.255.255.254",          # loopback
        "10.0.0.1", "172.16.0.1", "172.31.255.255", "192.168.1.1",   # private
        "169.254.169.254",                        # cloud metadata (link-local)
        "100.64.0.1",                             # carrier-grade NAT
        "0.0.0.0", "255.255.255.255",             # unspecified / broadcast
        "224.0.0.1",                              # multicast
        "::1", "::", "fe80::1", "fc00::1", "fd00::1",   # IPv6 loopback / unspecified / link-local / unique-local
        "::ffff:127.0.0.1", "::ffff:169.254.169.254", "::ffff:10.0.0.1",  # IPv4-mapped
        "64:ff9b::7f00:1",                        # NAT64 of 127.0.0.1
        "2002:7f00:1::1",                         # 6to4 of 127.0.0.1
    ],
)
def test_non_public_addresses_are_rejected(ip):
    assert is_public_address(ip) is False


def fake_resolver(*addresses):
    def resolve(host, port, type=None):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (a, port)) for a in addresses]
    return resolve


def test_resolve_public_returns_addresses_when_all_are_public():
    assert resolve_public("registry.example.com", resolver=fake_resolver("8.8.8.8", "1.1.1.1")) == ["1.1.1.1", "8.8.8.8"]


@pytest.mark.parametrize(
    "answers",
    [
        ("127.0.0.1",),
        ("169.254.169.254",),
        ("10.0.0.7",),
        ("8.8.8.8", "10.0.0.7"),   # one good answer and one private: still refused
        ("8.8.8.8", "127.0.0.1"),  # DNS-rebinding style mixed answer
        # the private address sorts AFTER the public one, so a check that only
        # looked at the first answer would miss it
        ("1.1.1.1", "10.0.0.7"),
        ("1.1.1.1", "169.254.169.254"),
        ("1.1.1.1", "192.168.0.1"),
    ],
)
def test_resolve_public_refuses_if_any_answer_is_non_public(answers):
    assert code_of(resolve_public, "registry.example.com", 443, fake_resolver(*answers)) == "non_public_address"


def test_resolve_public_refuses_an_empty_answer():
    assert code_of(resolve_public, "registry.example.com", 443, fake_resolver()) == "unresolvable"
