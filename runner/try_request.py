"""Read a "Prompt try" issue opened by the relay, check it, and hand the target to the workflow.

The issue body is written by people, so nothing from it reaches a shell: it is parsed here,
checked against strict patterns, and only the checked values are written to GITHUB_OUTPUT.

Usage (in the workflow):
    python -m runner.try_request
Reads ISSUE_BODY, ISSUE_AUTHOR_ASSOCIATION and GITHUB_OUTPUT from the environment.
"""

import json
import os
import sys

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from runner.constants import (
    AUTHOR_PATTERN,
    COMMIT_SHA_PATTERN,
    PREVIEW_TARGET_PREFIX,
    TRUSTED_AUTHOR_ASSOCIATIONS,
    TRY_ID_PATTERN,
    TRY_JSON_BLOCK_PATTERN,
)
from runner.errors import RunnerInputError


class TryRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    pr_number: int = Field(alias="prNumber", gt=0)
    commit: str
    try_id: str = Field(alias="tryId")
    author: str

    @field_validator("commit")
    @classmethod
    def _full_sha(cls, value: str) -> str:
        if not COMMIT_SHA_PATTERN.match(value):
            raise ValueError("commit must be a full 40-character commit id")
        return value

    @field_validator("try_id")
    @classmethod
    def _known_try_id(cls, value: str) -> str:
        if not TRY_ID_PATTERN.match(value):
            raise ValueError("tryId must look like t1730900000000")
        return value

    @field_validator("author")
    @classmethod
    def _short_name(cls, value: str) -> str:
        if not AUTHOR_PATTERN.match(value):
            raise ValueError("author must be a short name of lowercase letters, digits or dashes")
        return value


def parse_try_request(body: str, author_association: str) -> TryRequest:
    if author_association not in TRUSTED_AUTHOR_ASSOCIATIONS:
        raise RunnerInputError("Only people with access to this repo can start a run.")
    match = TRY_JSON_BLOCK_PATTERN.search(body)
    if not match:
        raise RunnerInputError("The issue has no ```json block with the try's details.")
    try:
        return TryRequest.model_validate(json.loads(match.group(1)))
    except (json.JSONDecodeError, ValidationError) as error:
        raise RunnerInputError(f"The try's details are not valid: {error}") from error


def main() -> int:
    try:
        request = parse_try_request(os.environ.get("ISSUE_BODY", ""), os.environ.get("ISSUE_AUTHOR_ASSOCIATION", ""))
    except RunnerInputError as error:
        print(f"Request refused: {error}", file=sys.stderr)
        return 2
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"target={PREVIEW_TARGET_PREFIX}{request.pr_number}\n")
        output.write(f"commit={request.commit}\n")
    print(f"Try {request.try_id} by {request.author}: pull request {request.pr_number} at {request.commit[:7]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
