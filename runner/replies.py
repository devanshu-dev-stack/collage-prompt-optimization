"""Check a reply's status and parse it into its typed shape, the same way for every call."""

from typing import TypeVar

from pydantic import BaseModel, ValidationError

from runner.api_client import RouteReply
from runner.errors import RunnerStepError
from runner.models import LessonStep

ReplyT = TypeVar("ReplyT", bound=BaseModel)
SUCCESS_STATUSES = (200, 201)


def check_reply(reply: RouteReply, model: type[ReplyT], step: LessonStep, what: str) -> ReplyT:
    if reply.status_code not in SUCCESS_STATUSES:
        # The body is CollageAI's structured error (message, code, trace id), which helps find the failure in its logs.
        raise RunnerStepError(f"{what} answered with status {reply.status_code}: {reply.body}", step)
    try:
        return model.model_validate(reply.body)
    except ValidationError as error:
        raise RunnerStepError(f"The {what} reply did not have the expected fields.", step) from error
