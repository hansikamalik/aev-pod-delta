from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
import typing

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .errors import OAuthError
from .http import HttpClient

GOOGLE_JWKS_ENDPOINT = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = frozenset(("accounts.google.com", "https://accounts.google.com"))


@dataclass(frozen=True, slots=True)
class GoogleIdentity:
    subject: str
    email: str | None
    email_verified: bool


class GoogleIdTokenVerifier:
    """Validates ID tokens before their identity claims are trusted."""

    def __init__(self, http_client: HttpClient) -> None:
        self._http = http_client
        self._keys: dict[str, typing.Mapping[str, typing.Any]] = {}
        self._keys_expire_at = 0.0

    def verify(self, token: str, expected_audience: str, expected_nonce: str) -> GoogleIdentity:
        header_part, payload_part, signature_part = self._split(token)
        header = self._decode_json(header_part)
        claims = self._decode_json(payload_part)
        kid = header.get("kid")
        if header.get("alg") != "RS256" or not isinstance(kid, str):
            raise OAuthError("Google ID token uses an unexpected signing algorithm.", "invalid_token_response")

        key = self._get_keys().get(kid)
        if key is None:
            # A rotation can happen before a cache entry expires; refresh once.
            self._keys_expire_at = 0
            key = self._get_keys().get(kid)
        if key is None:
            raise OAuthError("Google ID token signing key is unknown.", "invalid_token_response")
        self._verify_signature(key, f"{header_part}.{payload_part}".encode("ascii"), signature_part)
        self._verify_claims(claims, expected_audience, expected_nonce)

        return GoogleIdentity(
            subject=claims["sub"],
            email=claims.get("email") if isinstance(claims.get("email"), str) else None,
            email_verified=claims.get("email_verified") is True,
        )

    def _get_keys(self) -> dict[str, typing.Mapping[str, typing.Any]]:
        if self._keys and self._keys_expire_at > time.time():
            return self._keys
        try:
            response = self._http.get(GOOGLE_JWKS_ENDPOINT)
            body = response.json()
        except Exception as error:
            raise OAuthError("Google signing keys are unavailable.", "oauth_provider_error") from error
        if response.status != 200 or not isinstance(body, dict) or not isinstance(body.get("keys"), list):
            raise OAuthError("Google signing keys are unavailable.", "oauth_provider_error")

        keys: dict[str, typing.Mapping[str, typing.Any]] = {
            key["kid"]: typing.cast(typing.Mapping[str, typing.Any], key)
            for key in body["keys"]
            if isinstance(key, dict) and key.get("kty") == "RSA" and isinstance(key.get("kid"), str)
        }
        if not keys:
            raise OAuthError("Google signing keys are invalid.", "oauth_provider_error")
        self._keys = keys
        self._keys_expire_at = time.time() + _cache_ttl_seconds(response.headers.get("cache-control"))
        return keys

    @staticmethod
    def _verify_signature(key: typing.Mapping[str, typing.Any], message: bytes, signature_part: str) -> None:
        try:
            modulus = int.from_bytes(_b64url_decode(key["n"]), "big")
            exponent = int.from_bytes(_b64url_decode(key["e"]), "big")
            public_key = rsa.RSAPublicNumbers(exponent, modulus).public_key()
            public_key.verify(
                _b64url_decode(signature_part), message, padding.PKCS1v15(), hashes.SHA256()
            )
        except (InvalidSignature, KeyError, TypeError, ValueError) as error:
            raise OAuthError("Google ID token signature is invalid.", "invalid_token_response") from error

    @staticmethod
    def _verify_claims(claims: typing.Mapping[str, typing.Any], audience: str, nonce: str) -> None:
        token_audience = claims.get("aud")
        if isinstance(token_audience, str):
            audience_matches = token_audience == audience
        elif isinstance(token_audience, list):
            audience_matches = audience in token_audience and claims.get("azp") == audience
        else:
            audience_matches = False
        expires_at = claims.get("exp")
        valid_expiry = isinstance(expires_at, int) and not isinstance(expires_at, bool) and expires_at > time.time()
        if (
            claims.get("iss") not in GOOGLE_ISSUERS
            or not audience_matches
            or not valid_expiry
            or claims.get("nonce") != nonce
            or not isinstance(claims.get("sub"), str)
            or not claims["sub"]
        ):
            raise OAuthError("Google ID token claims are invalid.", "invalid_token_response")

    @staticmethod
    def _split(token: str) -> tuple[str, str, str]:
        pieces = token.split(".")
        if len(pieces) != 3 or not all(pieces):
            raise OAuthError("Google returned a malformed ID token.", "invalid_token_response")
        return pieces[0], pieces[1], pieces[2]

    @staticmethod
    def _decode_json(value: str) -> typing.Mapping[str, typing.Any]:
        try:
            decoded = json.loads(_b64url_decode(value).decode("utf-8"))
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
            raise OAuthError("Google returned an unreadable ID token.", "invalid_token_response") from error
        if not isinstance(decoded, dict):
            raise OAuthError("Google returned an unreadable ID token.", "invalid_token_response")
        return decoded


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _cache_ttl_seconds(cache_control: str | None) -> int:
    if cache_control:
        for directive in cache_control.split(","):
            name, _, value = directive.strip().partition("=")
            if name.lower() == "max-age" and value.isdecimal():
                return min(max(int(value), 300), 86_400)
    return 3600
