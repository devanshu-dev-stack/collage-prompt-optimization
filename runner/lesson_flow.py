"""Click through every lesson wizard step for one test case, through the real routes."""

import json
from pathlib import Path
from typing import Optional, TypeVar

from pydantic import BaseModel, JsonValue

from runner.api_client import CollageClient
from runner.constants import (
    CONCEPTS_PATH,
    CREATE_LESSON_PATH,
    OBJECTIVES_PATH,
    SCAFFOLD_PATH,
    SSE_ERROR_EVENT_TYPE,
    SSE_EVENT_TYPE_KEY,
    STREAM_PATH,
    TEXT_MATERIAL_SOURCE,
    UPLOAD_MATERIAL_SOURCE,
    UPLOAD_PATH,
)
from runner.errors import RunnerStepError
from runner.loaders import read_source_files, read_source_text
from runner.models import (
    ConceptsReply,
    LessonCase,
    LessonRunResult,
    LessonShellReply,
    LessonStep,
    ObjectivesReply,
    ScaffoldReply,
    StepRecord,
    UploadReply,
)
from runner.replies import check_reply
from runner.website_mirror import keep_first, normalize_concepts, normalize_objectives, scaffold_for_generate

ReplyT = TypeVar("ReplyT", bound=BaseModel)


def _post_step(
    client: CollageClient, result: LessonRunResult, step: LessonStep, path: str,
    fields: dict[str, str], reply_model: type[ReplyT], files: list[tuple[str, bytes, str]] | None = None,
) -> ReplyT:
    reply = client.post_form(path, fields, files)
    result.steps.append(StepRecord(step=step, status_code=reply.status_code, seconds=reply.seconds, reply=reply.body))
    return check_reply(reply, reply_model, step, f"The {step.value} step")


def _with_custom_instructions(fields: dict[str, str], custom_instructions: Optional[str]) -> dict[str, str]:
    # The website only sends custom instructions when the box is not empty.
    if custom_instructions and custom_instructions.strip():
        return {**fields, "customInstructions": custom_instructions.strip()}
    return fields


def run_lesson_case(
    client: CollageClient, course_id: str, case: LessonCase, case_dir: Path, result: LessonRunResult,
) -> str:
    """Run upload, objectives, concepts, plan, create and generate. Returns the new lesson id."""
    language = case.language
    upload_path = UPLOAD_PATH.format(course_id=course_id)
    if case.source_files:
        upload = _post_step(client, result, LessonStep.UPLOAD, upload_path, {"materialSource": UPLOAD_MATERIAL_SOURCE},
                            UploadReply, read_source_files(case_dir, case))
    else:
        upload = _post_step(client, result, LessonStep.UPLOAD, upload_path,
                            {"materialSource": TEXT_MATERIAL_SOURCE, "sourceText": read_source_text(case_dir, case)}, UploadReply)
    session_id = upload.data.upload_session_id

    objectives_reply = _post_step(
        client, result, LessonStep.OBJECTIVES, OBJECTIVES_PATH.format(course_id=course_id),
        {"uploadSessionId": session_id, "loCount": str(case.objective_count), "language": language}, ObjectivesReply,
    )
    objectives = keep_first(normalize_objectives(objectives_reply.data), case.keep_objectives)
    objective_texts = json.dumps([objective.text for objective in objectives])

    concepts_reply = _post_step(
        client, result, LessonStep.CONCEPTS, CONCEPTS_PATH.format(course_id=course_id),
        {"uploadSessionId": session_id, "conceptCount": str(case.concept_count), "language": language,
         "selectedLearningObjectives": objective_texts}, ConceptsReply,
    )
    concepts = keep_first(normalize_concepts(concepts_reply.data), case.keep_concepts)

    scaffold_fields = {
        "uploadSessionId": session_id, "conceptCount": str(len(concepts)), "language": language,
        "selectedConcepts": json.dumps([concept.model_dump(by_alias=True) for concept in concepts]),
        "selectedLearningObjectives": objective_texts,
    }
    scaffold = _post_step(client, result, LessonStep.SCAFFOLD, SCAFFOLD_PATH.format(course_id=course_id),
                          _with_custom_instructions(scaffold_fields, case.custom_instructions), ScaffoldReply)

    # The teacher accepts the plan as the AI wrote it.
    lesson_fields = {"uploadSessionId": session_id, "language": language,
                     "scaffold": json.dumps(scaffold_for_generate(objectives, scaffold.data.concepts))}
    lesson_title = (scaffold.lesson_title or "").strip()
    if lesson_title:
        lesson_fields["title"] = lesson_title
    shell = _post_step(client, result, LessonStep.CREATE_LESSON, CREATE_LESSON_PATH.format(course_id=course_id),
                       _with_custom_instructions(lesson_fields, case.custom_instructions), LessonShellReply)
    lesson_id = shell.data.id
    result.lesson_id = lesson_id

    _generate_content(client, result, course_id, lesson_id)
    return lesson_id


def _generate_content(client: CollageClient, result: LessonRunResult, course_id: str, lesson_id: str) -> None:
    """The step that writes every block. Its events are kept so failures inside the stream show up."""
    stream = client.read_stream(STREAM_PATH.format(course_id=course_id, lesson_id=lesson_id))
    result.stream_events = stream.events
    error_events = [
        event for event in stream.events
        if isinstance(event, dict) and event.get(SSE_EVENT_TYPE_KEY) == SSE_ERROR_EVENT_TYPE
    ]
    summary: dict[str, JsonValue] = {"events": len(stream.events), "errorEvents": len(error_events), "sawDone": stream.saw_done}
    result.steps.append(StepRecord(step=LessonStep.GENERATE_CONTENT, status_code=stream.status_code,
                                   seconds=stream.seconds, reply=summary))
    if stream.status_code != 200:
        raise RunnerStepError(f"Content generation answered with status {stream.status_code}.", LessonStep.GENERATE_CONTENT)
    if error_events:
        raise RunnerStepError(f"Content generation sent {len(error_events)} error event(s).", LessonStep.GENERATE_CONTENT)
    if not stream.saw_done:
        raise RunnerStepError("Content generation stopped before it finished.", LessonStep.GENERATE_CONTENT)
