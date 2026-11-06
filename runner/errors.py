"""Errors the runner raises on purpose, so main can report them in plain words."""

from typing import Optional

from runner.models import LessonStep


class RunnerInputError(Exception):
    """A test case, target or setting is wrong. Nothing has run yet."""


class RunnerStepError(Exception):
    """A call did not answer the way the website expects."""

    def __init__(self, message: str, step: Optional[LessonStep] = None) -> None:
        super().__init__(message)
        self.step = step
