"""Turn "dev" or "pr-<number>" into a CollageAI address, refusing any other host.

The runner logs in with the test teacher's password, so it must never be pointed at a
site we do not own.
"""

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from runner.constants import (
    DEV_TARGET_NAME,
    DEV_URL_ENV,
    PREVIEW_HOST_PATTERN,
    PREVIEW_TARGET_PREFIX,
    PREVIEW_URL_TEMPLATE,
    REQUIRED_SCHEME,
)
from runner.errors import RunnerInputError


@dataclass(frozen=True)
class Target:
    name: str
    base_url: str


def _check_https(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != REQUIRED_SCHEME or not parsed.hostname or parsed.path not in ("", "/"):
        raise RunnerInputError(f"Expected an https address with no path, got: {url}")
    return f"{REQUIRED_SCHEME}://{parsed.hostname}"


def resolve_target(name: str) -> Target:
    if name == DEV_TARGET_NAME:
        dev_url = os.environ.get(DEV_URL_ENV, "")
        if not dev_url:
            raise RunnerInputError(f"Set {DEV_URL_ENV} to the dev site's address to run against dev.")
        return Target(name, _check_https(dev_url))
    pr_number = name.removeprefix(PREVIEW_TARGET_PREFIX)
    if not name.startswith(PREVIEW_TARGET_PREFIX) or not pr_number.isdigit():
        raise RunnerInputError(f"Target must be '{DEV_TARGET_NAME}' or '{PREVIEW_TARGET_PREFIX}<PR number>', got: {name}")
    base_url = _check_https(PREVIEW_URL_TEMPLATE.format(pr_number=pr_number))
    if not PREVIEW_HOST_PATTERN.match(urlparse(base_url).hostname or ""):
        raise RunnerInputError(f"Not a CollageAI preview address: {base_url}")
    return Target(name, base_url)
