"""Wait until a preview is running the commit we want to test, so a run never tests the old build."""

import time

import requests
from pydantic import BaseModel, ValidationError

from runner.constants import (
    CONNECT_TIMEOUT_SECONDS,
    DEPLOY_POLL_SECONDS,
    DEPLOY_WAIT_TIMEOUT_SECONDS,
    STATUS_PATH,
)
from runner.errors import RunnerInputError


class StatusReply(BaseModel):
    commit: str | None = None


def _deployed_commit(base_url: str) -> tuple[bool, str | None]:
    """(reports a commit field, its value). A preview that is asleep or mid-deploy reads as not ready."""
    try:
        response = requests.get(base_url + STATUS_PATH, timeout=CONNECT_TIMEOUT_SECONDS)
        status = StatusReply.model_validate_json(response.content)
    except (requests.RequestException, ValidationError):
        return True, None
    return "commit" in status.model_fields_set, status.commit


def wait_for_commit(base_url: str, expected_commit: str) -> None:
    deadline = time.monotonic() + DEPLOY_WAIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        reports_commit, commit = _deployed_commit(base_url)
        if not reports_commit:
            raise RunnerInputError(
                "This preview does not report its commit. Start the experiment branch from a branch that "
                "includes CollageAI pull request #2094.",
            )
        if commit == expected_commit:
            return
        print(f"Waiting for {base_url} to deploy {expected_commit[:7]} (now: {(commit or 'not ready')[:7]})")
        time.sleep(DEPLOY_POLL_SECONDS)
    raise RunnerInputError(
        f"{base_url} did not deploy {expected_commit[:7]} within {DEPLOY_WAIT_TIMEOUT_SECONDS / 60:.0f} minutes. "
        "Check the pull request has the render-preview label and the deploy did not fail.",
    )
