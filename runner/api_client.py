"""Calls a CollageAI site over HTTPS the way the browser does: cookie login, CSRF header, form posts, event stream."""

import json
import time
from dataclasses import dataclass

import requests
from pydantic import JsonValue, TypeAdapter, ValidationError

from runner.constants import (
    CONNECT_TIMEOUT_SECONDS,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    LOGIN_PATH,
    READ_TIMEOUT_SECONDS,
    SSE_DATA_PREFIX,
    SSE_DONE_MARKER,
    UPLOAD_FILES_FIELD,
)
from runner.errors import RunnerStepError

_JSON: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)
_TIMEOUT = (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)


@dataclass(frozen=True)
class RouteReply:
    status_code: int
    seconds: float
    body: JsonValue


@dataclass(frozen=True)
class StreamReply:
    status_code: int
    seconds: float
    events: list[JsonValue]
    saw_done: bool


def _body(response: requests.Response) -> JsonValue:
    """The JSON body, or None when the site answered with something else (for example an HTML error page)."""
    try:
        return _JSON.validate_json(response.content)
    except ValidationError:
        return None


class CollageClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url
        self._session = requests.Session()

    def _url(self, path: str) -> str:
        return self._base_url + path

    def _csrf_headers(self) -> dict[str, str]:
        token = self._session.cookies.get(CSRF_COOKIE_NAME)
        if not token:
            raise RunnerStepError("No CSRF cookie. Log in first.")
        return {CSRF_HEADER_NAME: token}

    def login(self, email: str, password: str) -> None:
        response = self._session.post(self._url(LOGIN_PATH), json={"email": email, "password": password}, timeout=_TIMEOUT)
        if response.status_code != 200:
            raise RunnerStepError(f"Login failed with status {response.status_code}. Check the test teacher's email and password.")

    def get(self, path: str, params: dict[str, str] | None = None) -> RouteReply:
        started = time.monotonic()
        response = self._session.get(self._url(path), params=params, timeout=_TIMEOUT)
        return RouteReply(response.status_code, time.monotonic() - started, _body(response))

    def post_json(self, path: str, body: dict[str, str]) -> RouteReply:
        started = time.monotonic()
        response = self._session.post(self._url(path), json=body, headers=self._csrf_headers(), timeout=_TIMEOUT)
        return RouteReply(response.status_code, time.monotonic() - started, _body(response))

    def post_form(self, path: str, fields: dict[str, str], files: list[tuple[str, bytes, str]] | None = None) -> RouteReply:
        """A multipart form post, like the website's FormData calls. Files go under one repeated field."""
        started = time.monotonic()
        multipart: list[tuple[str, tuple[str | None, str | bytes] | tuple[str, bytes, str]]] = [
            (name, (None, value)) for name, value in fields.items()
        ]
        multipart += [(UPLOAD_FILES_FIELD, (file_name, content, media_type)) for file_name, content, media_type in files or []]
        response = self._session.post(self._url(path), files=multipart, headers=self._csrf_headers(), timeout=_TIMEOUT)
        return RouteReply(response.status_code, time.monotonic() - started, _body(response))

    def read_stream(self, path: str) -> StreamReply:
        """Read every server-sent event until [DONE]. Heartbeat comments and blank lines are skipped."""
        started = time.monotonic()
        events: list[JsonValue] = []
        saw_done = False
        with self._session.get(self._url(path), stream=True, timeout=_TIMEOUT) as response:
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith(SSE_DATA_PREFIX):
                    continue
                payload = line[len(SSE_DATA_PREFIX):]
                if payload.strip() == SSE_DONE_MARKER:
                    saw_done = True
                    break
                events.append(_JSON.validate_python(json.loads(payload)))
            status_code = response.status_code
        return StreamReply(status_code, time.monotonic() - started, events, saw_done)
