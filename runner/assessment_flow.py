"""Make one summative for a test case through the real routes, the way the summative wizard does."""

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, JsonValue

from runner.api_client import CollageClient, RouteReply
from runner.assessment_models import (
    AssessmentCase,
    AssessmentRunResult,
    AssessmentStep,
    AssessmentStepRecord,
    GenerateReply,
    SummativeReply,
)
from runner.constants import SUMMATIVE_GENERATE_PATH, SUMMATIVE_PATH, SUMMATIVE_UPLOAD_PATH
from runner.loaders import read_source_files, read_source_text
from runner.models import LessonCase, UploadReply
from runner.replies import check_reply

ReplyT = TypeVar("ReplyT", bound=BaseModel)


def _record(result: AssessmentRunResult, step: AssessmentStep, reply: RouteReply,
            model: type[ReplyT], what: str) -> ReplyT:
    result.steps.append(AssessmentStepRecord(step=step, status_code=reply.status_code, seconds=reply.seconds, reply=reply.body))
    return check_reply(reply, model, step, what)


def run_assessment_case(client: CollageClient, course_id: str, case: LessonCase, assessment: AssessmentCase,
                        case_dir: Path, result: AssessmentRunResult) -> str:
    """Upload the sources, generate the summative and read it back. Returns the summative id."""
    fields = {"courseId": course_id}
    if case.source_files:
        upload_reply = client.post_form(SUMMATIVE_UPLOAD_PATH, fields, read_source_files(case_dir, case))
    else:
        upload_reply = client.post_form(SUMMATIVE_UPLOAD_PATH, {**fields, "sourceText": read_source_text(case_dir, case)})
    session_id = _record(result, AssessmentStep.UPLOAD, upload_reply, UploadReply, "The upload step").data.upload_session_id

    body: dict[str, JsonValue] = {
        "courseId": course_id,
        "uploadSessionId": session_id,
        "language": case.language,
        "objectives": list(assessment.objectives),
        # One group with no supporting media, like a teacher who only picks question types.
        "questionGroups": [{"questionTypes": [spec.model_dump(mode="json", by_alias=True) for spec in assessment.questions]}],
    }
    if assessment.custom_instructions and assessment.custom_instructions.strip():
        body["customInstructions"] = assessment.custom_instructions.strip()
    generated = _record(result, AssessmentStep.GENERATE, client.post_json(SUMMATIVE_GENERATE_PATH, body),
                        GenerateReply, "The generate step")
    summative_id = generated.data.id

    read_reply = client.get(SUMMATIVE_PATH.format(summative_id=summative_id))
    result.summative = _record(result, AssessmentStep.READ, read_reply, SummativeReply, "Reading the summative").data
    # The full summative is kept once, in result.summative.
    result.steps[-1].reply = None
    return summative_id
