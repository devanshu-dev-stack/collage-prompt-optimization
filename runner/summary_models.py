"""Shapes for the comparison the shared page shows: the parts of a saved lesson we read, and the summary we write."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, JsonValue


# Parts of a saved lesson (from result.json), read once into typed shapes.

class BlockDoc(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    questions: list[JsonValue] = Field(default_factory=list)


class ObjectiveDoc(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str


class LessonDoc(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: Optional[str] = None
    learning_objectives: list[ObjectiveDoc | str] = Field(default_factory=list, alias="learningObjectives")


class ConceptDoc(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(alias="_id")
    title: str = ""
    blocks: list[BlockDoc] = Field(default_factory=list)


class ExerciseDoc(BaseModel):
    model_config = ConfigDict(extra="ignore")

    blocks: list[BlockDoc] = Field(default_factory=list)


# The summary written for the page and the issue comment.

class ConceptSummary(BaseModel):
    title: str
    block_types: dict[str, int]
    exercises: int
    quiz_questions: int


class CaseSummary(BaseModel):
    finished: bool
    failed_step: Optional[str]
    error: Optional[str]
    lesson_url: Optional[str]
    title: Optional[str]
    objectives: list[str]
    concepts: list[ConceptSummary]
    concept_block_types: dict[str, int]
    exercise_block_types: dict[str, int]
    exercises: int
    quiz_questions: int
    step_seconds: dict[str, float]


class CaseComparison(BaseModel):
    case_id: str
    baseline: Optional[CaseSummary]
    experiment: Optional[CaseSummary]


class RunSummary(BaseModel):
    issue: Optional[int]
    target: str
    commit: Optional[str]
    created_at: str
    cases: list[CaseComparison]
