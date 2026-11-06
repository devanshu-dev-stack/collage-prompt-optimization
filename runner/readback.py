"""Read the finished lesson and the AI token counts back from the throwaway database, always scoped by orgId."""

from collections.abc import Mapping

from bson import ObjectId, json_util
from pydantic import JsonValue, TypeAdapter

from runner.errors import RunnerStepError
from runner.models import LessonStep, TokenUsageRow, TokenUsageTotal

_JSON: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)


def _to_json(document: Mapping[str, object]) -> JsonValue:
    """Mongo types (ObjectId, dates) become plain JSON, so results are easy to read and diff."""
    return _JSON.validate_json(json_util.dumps(document, json_options=json_util.RELAXED_JSON_OPTIONS))


def read_lesson(org_id: ObjectId, lesson_id: str) -> tuple[JsonValue, list[JsonValue], list[JsonValue]]:
    """The lesson, its concepts (with blocks) and its exercises (with blocks), as saved."""
    from db.collections.factory import get_assessments, get_concepts, get_lessons

    lesson = get_lessons().get_by_id(ObjectId(lesson_id))
    if not lesson or lesson.get("orgId") != org_id:
        raise RunnerStepError("The finished lesson was not found in this run's organization.", LessonStep.GENERATE_CONTENT)
    concepts = get_concepts().get_concepts_by_lesson(org_id, lesson_id)
    exercises = get_assessments().get_exercises_by_lesson(org_id, lesson_id)
    return _to_json(lesson), [_to_json(c) for c in concepts], [_to_json(e) for e in exercises]


def read_token_usage(org_id: ObjectId, course_id: str) -> list[TokenUsageTotal]:
    """Tokens per AI feature and model for this case's course, to compare the cost of experiments."""
    from db.collections.factory import get_token_usage

    totals: dict[tuple[str, str | None], TokenUsageTotal] = {}
    for document in get_token_usage().find({"orgId": org_id, "courseId": ObjectId(course_id)}):
        row = TokenUsageRow.model_validate(document)
        key = (row.feature, row.model)
        total = totals.setdefault(key, TokenUsageTotal(feature=row.feature, model=row.model, calls=0,
                                                       input_tokens=0, output_tokens=0))
        total.calls += 1
        total.input_tokens += row.input_tokens
        total.output_tokens += row.output_tokens
    return list(totals.values())
