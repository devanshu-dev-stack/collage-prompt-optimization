"""Typed shapes for judging a summative: its checks, the judge's answer and the scores worked out from it."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from runner.judge_models import PromptBase


class CheckLevel(str, Enum):
    """Whether a check looks at the assessment as a whole or at one question."""

    ASSESSMENT = "assessment"
    QUESTION = "question"


class AssessmentCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    look_for: str
    points: int
    level: CheckLevel


class AssessmentProblem(BaseModel):
    check: str = Field(description="The id of the check this problem breaks")
    location: str = Field(description="'Question <n>', 'Questions <n> and <m>', or 'Whole assessment'")
    assessment_text: str = Field(description="The assessment's words, quoted exactly, or '' for a whole-assessment problem")
    source_text: str = Field(description="The source's words, 'not in source', or 'not about the source'")
    reason: str = Field(description="One sentence on why this is a problem")


class AssessmentJudgement(BaseModel):
    problems: list[AssessmentProblem]


class AssessmentSide(BaseModel):
    """One summative's judgement plus the totals the code works out from it."""

    problem_counts: dict[str, int]
    checked: list[str]
    questions: int
    points_lost: int
    # Assessment quality, 0-100: 100 minus the points lost per 10 questions (ASSESSMENT_JUDGE.md, "Score").
    score: int
    problems: list[AssessmentProblem]


# The parts of a saved summative the judge reads (CollageAI server/db/models/blocks/quiz.py).

class CriterionDoc(BaseModel):
    criterion: str
    weight: Optional[float] = None


class BlankDoc(BaseModel):
    blank_order: int = Field(alias="blankOrder")
    answer: str


class QuestionDoc(BaseModel):
    type: str
    question: str
    points: Optional[float] = None
    options: list[str] = Field(default_factory=list)
    correct_answers: list[str] = Field(default_factory=list, alias="correctAnswers")
    correct_answer: Optional[str] = Field(default=None, alias="correctAnswer")
    grading_criteria: list[CriterionDoc] = Field(default_factory=list, alias="gradingCriteria")
    blanks: list[BlankDoc] = Field(default_factory=list)
    explanation: Optional[str] = None
    correct_feedback: Optional[str] = Field(default=None, alias="correctFeedback")
    incorrect_feedback: Optional[str] = Field(default=None, alias="incorrectFeedback")


class SummativeBlockDoc(BaseModel):
    type: str
    text: Optional[str] = None
    questions: list[QuestionDoc] = Field(default_factory=list)


class SummativeSectionDoc(BaseModel):
    type: str
    blocks: list[SummativeBlockDoc] = Field(default_factory=list)


class SummativeDoc(BaseModel):
    title: Optional[str] = None
    sections: list[SummativeSectionDoc] = Field(default_factory=list)

    def questions(self) -> list[QuestionDoc]:
        return [question for section in self.sections for block in section.blocks for question in block.questions]


class AssessmentSummary(BaseModel):
    """The shape of one summative run, kept next to its judgement."""

    finished: bool
    failed_step: Optional[str]
    error: Optional[str]
    summative_url: Optional[str]
    title: Optional[str]
    objectives: list[str]
    questions: int
    question_types: dict[str, int]
    step_seconds: dict[str, float]


class AssessmentBaselineRun(BaseModel):
    summary: AssessmentSummary
    judgement: AssessmentSide


class AssessmentBaselineCase(BaseModel):
    case_id: str
    runs: list[AssessmentBaselineRun] = Field(min_length=1)


class AssessmentBaseline(BaseModel):
    """A version's fixed assessment score: summatives judged once and kept as the yardstick for every try."""

    kind: Literal["assessment"] = "assessment"
    base: PromptBase
    commit: str
    made_at: str
    cases: list[AssessmentBaselineCase]
