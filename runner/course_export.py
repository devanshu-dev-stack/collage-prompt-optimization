"""Read human-made lessons and summatives from a production course, without changing anything.

They become the human baseline: judged with the same checks, and compared with anything new.
The exporter logs in and then only reads (GET). Every write call fails on purpose.
The content is real course data, so it is saved under outputs/human/ (never in git).

Usage:
    python -m runner.course_export list --course <course id>
    python -m runner.course_export export --course <course id> [--lesson <id> ...] [--summative <id> ...]
Login: PROD_READER_EMAIL and PROD_READER_PASSWORD.
"""

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, JsonValue

from runner.api_client import CollageClient, RouteReply, StreamReply
from runner.assessment_models import AssessmentRunResult, AssessmentStep, SummativeReply
from runner.constants import (
    COURSE_LESSONS_PATH, HUMAN_EXPORT_DIR, HUMAN_TARGET_NAME, LESSON_PAGE_PATH, LESSON_SOURCES_PATH, LESSONS_MAX_PAGES,
    LESSONS_PAGE_SIZE, PROD_READER_EMAIL_ENV, PROD_READER_PASSWORD_ENV, PROD_URL, REQUIRED_SCHEME, RESULT_FILE_NAME,
    SOURCE_DOWNLOAD_MAX_BYTES, SOURCE_DOWNLOAD_TIMEOUT_SECONDS, SUMMATIVE_PAGE_PATH, SUMMATIVE_PATH, SUMMATIVES_PATH,
)
from runner.errors import RunnerStepError
from runner.lesson_reader import read_lesson
from runner.models import ItemWithId, JsonPage, LessonRunResult, LessonStep
from runner.replies import check_reply

ID_PATTERN = re.compile(r"^[0-9a-f]{24}$")
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
SUMMATIVE_FILE_NAME = "summative.json"
SOURCES_DIR = "sources"
MANIFEST_FILE_NAME = "manifest.json"
DOWNLOAD_CHUNK_BYTES = 64 * 1024
LESSON_STEP = LessonStep.READ_LESSON
SUMMATIVE_STEP = AssessmentStep.READ


class ReadOnlyClient(CollageClient):
    """A client that can log in and read, and nothing else, so an export can never change a course."""

    def post_json(self, path: str, body: dict[str, JsonValue]) -> RouteReply:
        raise RunnerStepError(f"Read only: refused a write to {path}.")

    def post_form(self, path: str, fields: dict[str, str], files: list[tuple[str, bytes, str]] | None = None) -> RouteReply:
        raise RunnerStepError(f"Read only: refused a write to {path}.")

    def read_stream(self, path: str) -> StreamReply:
        raise RunnerStepError(f"Read only: refused {path}.")


class LessonsPageReply(BaseModel):
    data: JsonPage


class ListReply(BaseModel):
    data: list[JsonValue]


class Titled(BaseModel):
    id: str
    title: str = ""

    @classmethod
    def of(cls, item: JsonValue) -> "Titled":
        title = item.get("title") if isinstance(item, dict) else None
        return cls(id=ItemWithId.model_validate(item).id, title=str(title or ""))


class SourceRecord(BaseModel):
    filename: str
    file_type: str
    saved_as: str | None
    note: str | None = None


class ExportManifest(BaseModel):
    course_id: str
    exported_at: str
    lessons: dict[str, str]
    summatives: dict[str, str]
    sources: dict[str, list[SourceRecord]]


def _check_id(value: str) -> str:
    if not ID_PATTERN.match(value):
        raise RunnerStepError(f"Not a course, lesson or summative id: {value!r}.")
    return value


def _login() -> ReadOnlyClient:
    email, password = os.environ.get(PROD_READER_EMAIL_ENV, ""), os.environ.get(PROD_READER_PASSWORD_ENV, "")
    if not email or not password:
        raise RunnerStepError(f"Set {PROD_READER_EMAIL_ENV} and {PROD_READER_PASSWORD_ENV}.")
    client = ReadOnlyClient(PROD_URL)
    client.login(email, password)
    return client


def list_lessons(client: ReadOnlyClient, course_id: str) -> list[Titled]:
    lessons: list[Titled] = []
    for page in range(1, LESSONS_MAX_PAGES + 1):
        reply = check_reply(client.get(COURSE_LESSONS_PATH.format(course_id=course_id),
                                       {"page": str(page), "limit": str(LESSONS_PAGE_SIZE)}),
                            LessonsPageReply, LESSON_STEP, "Listing lessons")
        lessons += [Titled.of(item) for item in reply.data.items]
        if len(reply.data.items) < LESSONS_PAGE_SIZE:
            break
    return lessons


def list_summatives(client: ReadOnlyClient, course_id: str) -> list[Titled]:
    reply = check_reply(client.get(SUMMATIVES_PATH, {"courseId": course_id}), ListReply, SUMMATIVE_STEP, "Listing summatives")
    return [Titled.of(item) for item in reply.data]


def _download(url: str, folder: Path, name: str) -> Path | None:
    """One source file over https, under the size limit. None when it cannot be fetched."""
    if urlparse(url).scheme != REQUIRED_SCHEME:
        return None
    try:
        with requests.get(url, timeout=SOURCE_DOWNLOAD_TIMEOUT_SECONDS, stream=True) as reply:
            if not reply.ok:
                return None
            data = bytearray()
            for chunk in reply.iter_content(DOWNLOAD_CHUNK_BYTES):
                data.extend(chunk)
                if len(data) > SOURCE_DOWNLOAD_MAX_BYTES:
                    return None
    except requests.RequestException:
        return None
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(bytes(data))
    return path


def export_sources(client: ReadOnlyClient, course_id: str, lesson_id: str, folder: Path) -> list[SourceRecord]:
    reply = check_reply(client.get(LESSON_SOURCES_PATH.format(course_id=course_id, lesson_id=lesson_id)),
                        ListReply, LESSON_STEP, "Reading lesson sources")
    records: list[SourceRecord] = []
    for number, item in enumerate(reply.data, start=1):
        source = item if isinstance(item, dict) else {}
        filename = str(source.get("filename") or f"source-{number}")
        safe = f"{number:02d}-{SAFE_NAME.sub('_', filename)[:120]}"
        saved = _download(str(source.get("url") or ""), folder, safe)
        records.append(SourceRecord(filename=filename, file_type=str(source.get("fileType") or ""),
                                    saved_as=saved.name if saved else None,
                                    note=None if saved else "could not download"))
    return records


def export_lesson(client: ReadOnlyClient, course_id: str, lesson_id: str, out: Path) -> tuple[str, list[SourceRecord]]:
    """The lesson as the judge reads it (result.json, like a run's), plus its source files."""
    folder = out / "lessons" / lesson_id
    result = LessonRunResult(case_id=f"human-{lesson_id}", target=HUMAN_TARGET_NAME, base_url=PROD_URL,
                             started_at=datetime.now(UTC).isoformat(), course_id=course_id, lesson_id=lesson_id,
                             lesson_url=PROD_URL + LESSON_PAGE_PATH.format(course_id=course_id, lesson_id=lesson_id))
    read_lesson(client, course_id, lesson_id, result)
    result.finished = True
    folder.mkdir(parents=True, exist_ok=True)
    (folder / RESULT_FILE_NAME).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    sources = export_sources(client, course_id, lesson_id, folder / SOURCES_DIR)
    title = result.lesson.get("title") if isinstance(result.lesson, dict) else ""
    return str(title or ""), sources


def export_summative(client: ReadOnlyClient, course_id: str, summative_id: str, out: Path) -> str:
    folder = out / "summatives" / summative_id
    summative = check_reply(client.get(SUMMATIVE_PATH.format(summative_id=summative_id)), SummativeReply, SUMMATIVE_STEP,
                            "Reading the summative").data
    result = AssessmentRunResult(
        case_id=f"human-{summative_id}", target=HUMAN_TARGET_NAME, base_url=PROD_URL,
        started_at=datetime.now(UTC).isoformat(), finished=True, course_id=course_id, summative_id=summative_id,
        summative_url=PROD_URL + SUMMATIVE_PAGE_PATH.format(course_id=course_id, summative_id=summative_id),
        summative=summative)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / RESULT_FILE_NAME).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    title = summative.get("title") if isinstance(summative, dict) else ""
    return str(title or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read human-made lessons and summatives from production (read only).")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="Show a course's lessons and summatives.")
    listing.add_argument("--course", required=True)
    export = commands.add_parser("export", help="Save chosen lessons and summatives, with lesson sources.")
    export.add_argument("--course", required=True)
    export.add_argument("--lesson", action="append", default=[])
    export.add_argument("--summative", action="append", default=[])
    args = parser.parse_args()
    try:
        course_id = _check_id(args.course)
        client = _login()
        if args.command == "list":
            for kind, items in (("lesson", list_lessons(client, course_id)), ("summative", list_summatives(client, course_id))):
                for item in items:
                    print(f"{kind}\t{item.id}\t{item.title}")
            return 0
        lesson_ids = [_check_id(value) for value in args.lesson]
        summative_ids = [_check_id(value) for value in args.summative]
        if not lesson_ids and not summative_ids:
            raise RunnerStepError("Name at least one --lesson or --summative.")
        out = Path(HUMAN_EXPORT_DIR) / course_id
        manifest = ExportManifest(course_id=course_id, exported_at=datetime.now(UTC).isoformat(),
                                  lessons={}, summatives={}, sources={})
        for lesson_id in lesson_ids:
            title, sources = export_lesson(client, course_id, lesson_id, out)
            manifest.lessons[lesson_id], manifest.sources[lesson_id] = title, sources
            print(f"lesson {lesson_id}: {title} ({sum(1 for s in sources if s.saved_as)}/{len(sources)} sources saved)")
        for summative_id in summative_ids:
            manifest.summatives[summative_id] = export_summative(client, course_id, summative_id, out)
            print(f"summative {summative_id}: {manifest.summatives[summative_id]}")
        (out / MANIFEST_FILE_NAME).write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        print(f"Saved under {out}")
    except RunnerStepError as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
