"""The judge's answer for one lesson (see JUDGE.md). Also used as the output schema of the judge call."""

from enum import Enum

from pydantic import BaseModel, Field

from runner.summary_models import CaseSummary


class Check(str, Enum):
    INVENTED_QUOTE = "invented_quote"
    INEXACT_QUOTE = "inexact_quote"
    MISATTRIBUTED_QUOTE = "misattributed_quote"
    FACTUAL_ERROR = "factual_error"
    WRONG_VIEWPOINT = "wrong_viewpoint"
    OFF_SOURCE_CONTENT = "off_source_content"
    IGNORES_CUSTOM_INSTRUCTIONS = "ignores_custom_instructions"


# Lessons judged before `checked` was recorded were judged on these five only.
FIRST_CHECKS: list[str] = [
    Check.INVENTED_QUOTE.value, Check.MISATTRIBUTED_QUOTE.value, Check.FACTUAL_ERROR.value,
    Check.WRONG_VIEWPOINT.value, Check.OFF_SOURCE_CONTENT.value,
]


class ExtraCheck(BaseModel):
    """A check someone added on the page and Claude accepted. Its points work like the built-in checks'."""

    id: str = Field(pattern=r"^x\d{1,4}$")
    name: str = Field(min_length=1, max_length=80)
    look_for: str = Field(min_length=15, max_length=600, description="What counts as a problem, in plain words")
    points: int = Field(ge=1, le=10)


class ExtraChecks(BaseModel):
    checks: list[ExtraCheck]


class Problem(BaseModel):
    check: str = Field(description="The id of the check this problem breaks, from the checklist or the extra checks")
    location: str = Field(description="Concept or exercise title, and block number")
    lesson_text: str = Field(description="The lesson's words, quoted exactly")
    source_text: str = Field(description="The source's words, or 'not in source'")
    reason: str = Field(description="One sentence on why this is a problem")


class Example(BaseModel):
    location: str = Field(description="Concept or exercise title, and block number")
    summary: str = Field(description="The example in a few words")
    from_source: bool = Field(
        description="True when it is the source's own case, even if reframed for the audience the custom instructions name, as long as its people, facts and numbers are kept"
    )
    source_had_one: bool = Field(
        description="Only for an example not from the source: true when the source has an example that fits the same concept"
    )


class LessonJudgement(BaseModel):
    problems: list[Problem]
    examples: list[Example]


class SideJudgement(BaseModel):
    """One lesson's judgement plus the totals the code works out from it."""

    problem_counts: dict[str, int]
    examples_total: int
    examples_from_source: int
    # Made up although the source had an example that fits the same concept.
    made_up_examples: int
    # Every check this lesson was judged on, so a page can show "-" for a check added later.
    checked: list[str] = Field(default_factory=lambda: list(FIRST_CHECKS))
    concepts: int
    points_lost: int
    # Source accuracy, 0-100, worked out by the code from the problems (see JUDGE.md, "Score").
    score: int
    # Follows the custom instructions, 0-100: 100 minus the points per problem, for the whole lesson.
    # None for lessons judged before this check existed.
    instructions_score: int | None = None
    problems: list[Problem]
    examples: list[Example]


class CaseJudgement(BaseModel):
    case_id: str
    baseline: SideJudgement | None
    experiment: SideJudgement | None


class TryJudgement(BaseModel):
    judged_at: str
    cases: list[CaseJudgement]


class PromptBase(str, Enum):
    """The prompt versions a try can start from (the page's BASES)."""

    DEV = "dev"
    PR2097 = "pr2097"


class BaselineRun(BaseModel):
    """One lesson made with a version's own prompts: its structure and its judgement."""

    summary: CaseSummary
    judgement: SideJudgement


class BaselineCase(BaseModel):
    case_id: str
    runs: list[BaselineRun] = Field(min_length=1)


class Baseline(BaseModel):
    """A version's fixed score: lessons judged once and kept as the yardstick for every try."""

    base: PromptBase
    commit: str
    made_at: str
    cases: list[BaselineCase]
