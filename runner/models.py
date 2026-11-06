"""Typed shapes for what the runner reads (test cases, route replies) and writes (results)."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from runner.constants import WEBSITE_CONCEPT_COUNT, WEBSITE_OBJECTIVE_COUNT


class LessonCase(BaseModel):
    """test-set/<case>/case.yaml: one lesson a teacher would make."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    course_title: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    language: str = Field(min_length=1)
    source_file: str = Field(min_length=1)
    custom_instructions: Optional[str] = None
    objective_count: int = Field(default=WEBSITE_OBJECTIVE_COUNT, ge=1)
    concept_count: int = Field(default=WEBSITE_CONCEPT_COUNT, ge=1)
    # What the teacher keeps. Left out means keep everything, which is the website's default.
    keep_objectives: Optional[int] = Field(default=None, ge=1)
    keep_concepts: Optional[int] = Field(default=None, ge=1)


class LessonStep(str, Enum):
    COURSE = "course"
    UPLOAD = "upload"
    OBJECTIVES = "objectives"
    CONCEPTS = "concepts"
    SCAFFOLD = "scaffold"
    CREATE_LESSON = "create_lesson"
    GENERATE_CONTENT = "generate_content"
    READ_LESSON = "read_lesson"


# Route replies. Only the fields the next step needs are declared; the full reply is kept in StepRecord.

class UploadData(BaseModel):
    upload_session_id: str = Field(alias="uploadSessionId")


class UploadReply(BaseModel):
    data: UploadData


class RawObjective(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    text: str


class ObjectivesReply(BaseModel):
    data: list[RawObjective | str]


class RawConcept(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    description: Optional[str] = None


class ConceptsReply(BaseModel):
    data: list[RawConcept]


class ScaffoldExercise(BaseModel):
    # Extra fields are kept: the website sends the plan back with every field it got.
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: Optional[str] = Field(default=None, alias="_id")
    type: Optional[str] = None
    question_subject: Optional[str] = Field(default=None, alias="questionSubject")


class ScaffoldConcept(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: Optional[str] = Field(default=None, alias="_id")
    title: Optional[str] = None
    exercises: list[ScaffoldExercise] = Field(default_factory=list)


class ScaffoldData(BaseModel):
    concepts: list[ScaffoldConcept] = Field(default_factory=list)


class ScaffoldReply(BaseModel):
    data: ScaffoldData
    lesson_title: Optional[str] = Field(default=None, alias="lessonTitle")


class LessonShellData(BaseModel):
    id: str = Field(alias="_id")


class LessonShellReply(BaseModel):
    data: LessonShellData


class SelectedObjective(BaseModel):
    """An objective the way the website keeps it: an id and its text."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    text: str


class CourseItem(BaseModel):
    id: str = Field(alias="_id")
    title: str


class CoursesPage(BaseModel):
    items: list[CourseItem]


class CoursesReply(BaseModel):
    data: CoursesPage


class CreatedCourseReply(BaseModel):
    data: CourseItem


class ItemWithId(BaseModel):
    """Any saved document; only its id is needed to fetch what belongs to it."""

    id: str = Field(alias="_id")


class JsonPage(BaseModel):
    items: list[JsonValue]


class LessonReply(BaseModel):
    data: JsonValue


class ConceptsPageReply(BaseModel):
    data: JsonPage


class AssessmentsReply(BaseModel):
    # The route answers with a plain list, or a page when paging is asked for.
    data: list[JsonValue] | JsonPage


# Results

class StepRecord(BaseModel):
    step: LessonStep
    status_code: int
    seconds: float
    reply: JsonValue


class LessonRunResult(BaseModel):
    case_id: str
    target: str
    base_url: str
    started_at: str
    finished: bool = False
    failed_step: Optional[LessonStep] = None
    error: Optional[str] = None
    course_id: Optional[str] = None
    lesson_id: Optional[str] = None
    lesson_url: Optional[str] = None
    steps: list[StepRecord] = Field(default_factory=list)
    stream_events: list[JsonValue] = Field(default_factory=list)
    lesson: JsonValue = None
    concepts: list[JsonValue] = Field(default_factory=list)
    exercises_by_concept: dict[str, list[JsonValue]] = Field(default_factory=dict)
    formatives: list[JsonValue] = Field(default_factory=list)
