"""Read the finished lesson the way the lesson page does (client/src/hooks/use-lesson-with-content.ts)."""

from pydantic import JsonValue

from runner.api_client import CollageClient
from runner.constants import (
    ASSESSMENTS_PATH,
    CONCEPTS_PAGE_LIMIT,
    EXERCISE_MODE,
    FORMATIVE_MODE,
    LESSON_CONCEPTS_PATH,
    LESSON_PATH,
)
from runner.models import AssessmentsReply, ConceptsPageReply, ItemWithId, JsonPage, LessonReply, LessonRunResult, LessonStep
from runner.replies import check_reply

STEP = LessonStep.READ_LESSON


def _assessments(client: CollageClient, params: dict[str, str], what: str) -> list[JsonValue]:
    reply = check_reply(client.get(ASSESSMENTS_PATH, params), AssessmentsReply, STEP, what)
    return reply.data.items if isinstance(reply.data, JsonPage) else reply.data


def read_lesson(client: CollageClient, course_id: str, lesson_id: str, result: LessonRunResult) -> None:
    """The lesson, its concepts (with blocks), each concept's exercises (with questions) and its formatives."""
    lesson_path = LESSON_PATH.format(course_id=course_id, lesson_id=lesson_id)
    result.lesson = check_reply(client.get(lesson_path), LessonReply, STEP, "Reading the lesson").data

    concepts_path = LESSON_CONCEPTS_PATH.format(course_id=course_id, lesson_id=lesson_id)
    concepts_page = check_reply(
        client.get(concepts_path, {"page": "1", "limit": str(CONCEPTS_PAGE_LIMIT)}), ConceptsPageReply, STEP, "Reading concepts",
    )
    result.concepts = concepts_page.data.items
    for concept in result.concepts:
        concept_id = ItemWithId.model_validate(concept).id
        result.exercises_by_concept[concept_id] = _assessments(client, {
            "courseId": course_id, "lessonId": lesson_id, "conceptId": concept_id,
            "mode": EXERCISE_MODE, "withQuestions": "true",
        }, "Reading exercises")
    result.formatives = _assessments(
        client, {"courseId": course_id, "lessonId": lesson_id, "mode": FORMATIVE_MODE}, "Reading formatives",
    )
