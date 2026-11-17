"""Typed shapes for the assessment pipeline: its test settings, route replies and saved results."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from runner.constants import MAX_SUMMATIVE_QUESTIONS


class AssessmentStep(str, Enum):
    COURSE = "course"
    UPLOAD = "upload"
    GENERATE = "generate"
    READ = "read_summative"


class QuestionType(str, Enum):
    """CollageAI's summative question types (server/api/schemas/summative_schemas.py)."""

    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    OPEN_ENDED = "open_ended"
    FILL_IN = "fill_in"


class BloomLevel(str, Enum):
    """CollageAI's thinking levels (server/db/models/scaffold.py BloomLevel)."""

    KNOWLEDGE = "knowledge"
    COMPREHENSION = "comprehension"
    APPLICATION = "application"
    ANALYSIS = "analysis"
    EVALUATION = "evaluation"
    CREATION = "creation"


class QuestionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: QuestionType
    bloom_type: BloomLevel = Field(serialization_alias="bloomType")
    quantity: int = Field(ge=1)


class AssessmentCase(BaseModel):
    """test-set/<case>/assessment.yaml: the same objectives and question mix for every run."""

    model_config = ConfigDict(extra="forbid")

    objectives: list[str] = Field(min_length=1)
    questions: list[QuestionSpec] = Field(min_length=1)
    custom_instructions: Optional[str] = None

    @property
    def question_count(self) -> int:
        return sum(spec.quantity for spec in self.questions)

    @model_validator(mode="after")
    def _within_limit(self) -> "AssessmentCase":
        if self.question_count > MAX_SUMMATIVE_QUESTIONS:
            raise ValueError(f"At most {MAX_SUMMATIVE_QUESTIONS} questions in one assessment.")
        return self


class GeneratedSummative(BaseModel):
    id: str = Field(alias="_id")


class GenerateReply(BaseModel):
    data: GeneratedSummative


class SummativeReply(BaseModel):
    data: JsonValue


class AssessmentStepRecord(BaseModel):
    step: AssessmentStep
    status_code: int
    seconds: float
    reply: JsonValue


class AssessmentRunResult(BaseModel):
    case_id: str
    target: str
    base_url: str
    started_at: str
    finished: bool = False
    failed_step: Optional[AssessmentStep] = None
    error: Optional[str] = None
    course_id: Optional[str] = None
    summative_id: Optional[str] = None
    summative_url: Optional[str] = None
    objectives: list[str] = Field(default_factory=list)
    questions_asked: int = 0
    steps: list[AssessmentStepRecord] = Field(default_factory=list)
    summative: JsonValue = None
