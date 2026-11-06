"""Calls the real CollageAI routes in-process, the way the browser does: cookie login, CSRF header, form posts, event stream."""

import json
import time
from dataclasses import dataclass

from flask import Flask
from pydantic import JsonValue, TypeAdapter, ValidationError

from runner.constants import (
    LOGIN_PATH,
    SSE_DATA_PREFIX,
    SSE_DONE_MARKER,
    SSE_EVENT_SEPARATOR,
)
from runner.errors import RunnerStepError

_JSON: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)


def _wire_json(raw: bytes) -> JsonValue:
    """The body exactly as the browser gets it (camelCase keys).

    Flask's get_json() would run the app's camelCase-to-snake_case converter, so it is not used.
    A body that is not JSON (for example an HTML error page) becomes None.
    """
    try:
        return _JSON.validate_json(raw)
    except ValidationError:
        return None


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


class WizardClient:
    def __init__(self, app: Flask) -> None:
        self._client = app.test_client()
        # Read from the app, so a rename in app.py cannot break the runner silently.
        self._csrf_cookie_name: str = app.config["JWT_ACCESS_CSRF_COOKIE_NAME"]
        self._csrf_header_name: str = app.config["JWT_ACCESS_CSRF_HEADER_NAME"]

    def login(self, email: str, password: str) -> None:
        response = self._client.post(LOGIN_PATH, json={"email": email, "password": password})
        if response.status_code != 200:
            raise RunnerStepError(f"Login failed with status {response.status_code}.")

    def _csrf_headers(self) -> dict[str, str]:
        cookie = self._client.get_cookie(self._csrf_cookie_name)
        if cookie is None:
            raise RunnerStepError("No CSRF cookie after login.")
        return {self._csrf_header_name: cookie.value}

    def post_form(self, path: str, fields: dict[str, str]) -> RouteReply:
        started = time.monotonic()
        response = self._client.post(
            path, data=fields, content_type="multipart/form-data", headers=self._csrf_headers(),
        )
        return RouteReply(response.status_code, time.monotonic() - started, _wire_json(response.get_data()))

    def read_stream(self, path: str) -> StreamReply:
        """Read every server-sent event until [DONE], skipping heartbeat comments."""
        started = time.monotonic()
        response = self._client.get(path, buffered=False)
        events: list[JsonValue] = []
        saw_done = False
        buffer = ""
        try:
            for chunk in response.response:
                buffer += chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
                *complete, buffer = buffer.split(SSE_EVENT_SEPARATOR)
                for raw_event in complete:
                    if not raw_event.startswith(SSE_DATA_PREFIX):
                        continue
                    payload = raw_event[len(SSE_DATA_PREFIX):]
                    if payload.strip() == SSE_DONE_MARKER:
                        saw_done = True
                        continue
                    events.append(_JSON.validate_python(json.loads(payload)))
        finally:
            response.close()
        return StreamReply(response.status_code, time.monotonic() - started, events, saw_done)
