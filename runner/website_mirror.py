"""What the website does between wizard steps, so each route gets the same input a teacher's browser sends.

Mirrors client/src/components/lesson-wizard/utils/learning-objectives-generation.ts,
concepts-generation.ts and the scaffold handling in client/src/pages/lesson-wizard-page.tsx.
If those files change, update this one.
"""

import uuid
from typing import Optional, TypeVar

from pydantic import JsonValue, TypeAdapter

from runner.constants import WEBSITE_DEFAULT_EXERCISE_TYPE
from runner.models import RawConcept, RawObjective, ScaffoldConcept, ScaffoldExercise, SelectedObjective

ItemT = TypeVar("ItemT")
_JSON_OBJECT = TypeAdapter(dict[str, JsonValue])


def _unique_id(requested: Optional[str], used: set[str]) -> str:
    """Keep the model's id unless it is empty or already taken, like the website."""
    chosen = requested if requested and requested not in used else str(uuid.uuid4())
    used.add(chosen)
    return chosen


def normalize_objectives(raw: list[RawObjective | str]) -> list[SelectedObjective]:
    used: set[str] = set()
    return [
        SelectedObjective(_id=_unique_id(None, used), text=item)
        if isinstance(item, str)
        else SelectedObjective(_id=_unique_id(item.id, used), text=item.text)
        for item in raw
    ]


def normalize_concepts(raw: list[RawConcept]) -> list[RawConcept]:
    used: set[str] = set()
    return [RawConcept(_id=_unique_id(c.id, used), title=c.title, description=c.description or "") for c in raw]


def keep_first(items: list[ItemT], limit: Optional[int]) -> list[ItemT]:
    """The teacher's pick: the first `limit` items, or all of them when no limit is set."""
    return items if limit is None else items[:limit]


def _exercise_for_generate(exercise: ScaffoldExercise) -> dict[str, JsonValue]:
    kept = _JSON_OBJECT.validate_python(exercise.model_dump(by_alias=True, exclude={"id", "type", "question_subject"}))
    return {
        **kept,
        "_id": exercise.id or str(uuid.uuid4()),
        "type": exercise.type or WEBSITE_DEFAULT_EXERCISE_TYPE,
        "questionSubject": exercise.question_subject or "",
    }


def scaffold_for_generate(objectives: list[SelectedObjective], concepts: list[ScaffoldConcept]) -> dict[str, JsonValue]:
    """The plan the website sends to "Generate": the kept objectives plus the plan's concepts with ids filled in."""
    plan_concepts: list[JsonValue] = []
    for concept in concepts:
        kept = _JSON_OBJECT.validate_python(concept.model_dump(by_alias=True, exclude={"id", "title", "exercises"}))
        plan_concepts.append({
            **kept,
            "_id": concept.id or str(uuid.uuid4()),
            "title": concept.title or "",
            "exercises": [_exercise_for_generate(exercise) for exercise in concept.exercises],
        })
    learning_objectives: list[JsonValue] = [{"_id": item.id, "text": item.text} for item in objectives]
    return {"learningObjectives": learning_objectives, "concepts": plan_concepts}
