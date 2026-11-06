"""The judge's answer for one lesson (see JUDGE.md). Also used as the output schema of the judge call."""

from enum import Enum

from pydantic import BaseModel, Field


class Check(str, Enum):
    INVENTED_QUOTE = "invented_quote"
    MISATTRIBUTED_QUOTE = "misattributed_quote"
    FACTUAL_ERROR = "factual_error"
    WRONG_VIEWPOINT = "wrong_viewpoint"
    OFF_SOURCE_CONTENT = "off_source_content"


class Problem(BaseModel):
    check: Check
    location: str = Field(description="Concept or exercise title, and block number")
    lesson_text: str = Field(description="The lesson's words, quoted exactly")
    source_text: str = Field(description="The source's words, or 'not in source'")
    reason: str = Field(description="One sentence on why this is a problem")


class Example(BaseModel):
    location: str = Field(description="Concept or exercise title, and block number")
    summary: str = Field(description="The example in a few words")
    from_source: bool


class LessonJudgement(BaseModel):
    problems: list[Problem]
    examples: list[Example]
