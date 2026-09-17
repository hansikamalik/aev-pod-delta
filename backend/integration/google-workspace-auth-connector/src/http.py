from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    body: bytes
    headers: Mapping[str, str]

    def json(self) -> object:
        return json.loads(self.body.decode("utf-8"))


class HttpClient(Protocol):
    def get(self, url: str) -> HttpResponse: ...

    def post_form(self, url: str, fields: Mapping[str, str]) -> HttpResponse: ...


class UrllibHttpClient:
    """Minimal HTTP client with a finite timeout and redirects disabled."""

    def __init__(self, timeout_seconds: float = 15) -> None:
        self._timeout_seconds = timeout_seconds
        self._opener = build_opener(_NoRedirectHandler())

    def get(self, url: str) -> HttpResponse:
        return self._request(Request(url, method="GET"))

    def post_form(self, url: str, fields: Mapping[str, str]) -> HttpResponse:
        request = Request(
            url,
            data=urlencode(fields).encode("ascii"),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return self._request(request)

    def _request(self, request: Request) -> HttpResponse:
        try:
            with self._opener.open(request, timeout=self._timeout_seconds) as response:
                return HttpResponse(
                    response.status,
                    response.read(),
                    {key.lower(): value for key, value in response.headers.items()},
                )
        except HTTPError as error:
            return HttpResponse(
                error.code,
                error.read(),
                {key.lower(): value for key, value in error.headers.items()} if error.headers else {},
            )


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None
