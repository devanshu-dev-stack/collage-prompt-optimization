"""Shapes for prompt text pulled out of CollageAI's Python files, and for edits to it."""

from pydantic import BaseModel, Field


class PromptSegment(BaseModel):
    """One block of prompt text as people see it. Fill-in values show as «name» markers."""

    id: str
    label: str
    text: str
    placeholders: list[str] = Field(default_factory=list)


class FileSegments(BaseModel):
    path: str
    dev_commit: str = Field(alias="devCommit")
    segments: list[PromptSegment]

    model_config = {"populate_by_name": True}


class SegmentEdit(BaseModel):
    id: str
    text: str


class FileEdits(BaseModel):
    path: str
    segments: list[SegmentEdit]
