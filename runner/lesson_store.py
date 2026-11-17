"""Keep every judged lesson, so a new or reworded check re-judges the same lessons instead of new ones.

The store is a folder holding the `lessons` branch (RELAY.md, "Stored lessons"): one folder per
lesson id with its result.json (gzip), the judge's answer and the checked side, plus index.json,
which lists each lesson's address, test case and the fixed scores and tries that use it.

Usage:
    python -m runner.lesson_store save --store <folder> --result <result.json> \\
        --judgement <answer.json> --side <side.json> --used-by <baseline or try id> [--used-by ...]
    python -m runner.lesson_store get --store <folder> --lesson-url <url> --out <folder>
"""

import argparse
import gzip
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from runner.constants import (
    LESSON_ID_PATTERN,
    LESSON_INDEX_FILE_NAME,
    RESULT_FILE_NAME,
    STORED_ANSWER_FILE_NAME,
    STORED_RESULT_FILE_NAME,
    STORED_SIDE_FILE_NAME,
)
from runner.judge_models import LessonJudgement, SideJudgement
from runner.models import LessonRunResult


class StoredLesson(BaseModel):
    lesson_url: str
    case_id: str
    used_by: list[str] = Field(default_factory=list)
    saved_at: str


class LessonIndex(BaseModel):
    lessons: dict[str, StoredLesson] = Field(default_factory=dict)


def _read_index(store: Path) -> LessonIndex:
    path = store / LESSON_INDEX_FILE_NAME
    return LessonIndex.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else LessonIndex()


def save_lesson(store: Path, result_path: Path, answer_path: Path, side_path: Path, used_by: list[str]) -> str:
    """Store one judged lesson. Saving it again replaces its judgement and adds to `used_by`."""
    raw = result_path.read_bytes()
    result = LessonRunResult.model_validate_json(raw)
    if not result.finished or not result.lesson_id or not result.lesson_url:
        raise ValueError(f"{result_path} is not a finished lesson.")
    if not LESSON_ID_PATTERN.fullmatch(result.lesson_id):
        raise ValueError(f"{result_path} has an unexpected lesson id.")
    LessonJudgement.model_validate_json(answer_path.read_text(encoding="utf-8"))
    SideJudgement.model_validate_json(side_path.read_text(encoding="utf-8"))

    folder = store / result.lesson_id
    folder.mkdir(parents=True, exist_ok=True)
    # mtime=0 keeps the file the same when the same lesson is saved again.
    (folder / STORED_RESULT_FILE_NAME).write_bytes(gzip.compress(raw, mtime=0))
    shutil.copyfile(answer_path, folder / STORED_ANSWER_FILE_NAME)
    shutil.copyfile(side_path, folder / STORED_SIDE_FILE_NAME)

    index = _read_index(store)
    earlier = index.lessons.get(result.lesson_id)
    index.lessons[result.lesson_id] = StoredLesson(
        lesson_url=result.lesson_url, case_id=result.case_id,
        used_by=sorted(set((earlier.used_by if earlier else []) + used_by)),
        saved_at=datetime.now(UTC).isoformat(),
    )
    index.lessons = dict(sorted(index.lessons.items()))
    (store / LESSON_INDEX_FILE_NAME).write_text(index.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result.lesson_id


def get_lesson(store: Path, lesson_url: str, out: Path) -> Path:
    """Unpack a stored lesson into `out/<lesson id>/` and return that folder."""
    found = [lesson_id for lesson_id, lesson in _read_index(store).lessons.items() if lesson.lesson_url == lesson_url]
    if not found:
        raise ValueError(f"No stored lesson for {lesson_url}.")
    source, target = store / found[0], out / found[0]
    target.mkdir(parents=True, exist_ok=True)
    (target / RESULT_FILE_NAME).write_bytes(gzip.decompress((source / STORED_RESULT_FILE_NAME).read_bytes()))
    shutil.copyfile(source / STORED_ANSWER_FILE_NAME, target / STORED_ANSWER_FILE_NAME)
    shutil.copyfile(source / STORED_SIDE_FILE_NAME, target / STORED_SIDE_FILE_NAME)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep judged lessons on the lessons branch, and get them back.")
    commands = parser.add_subparsers(dest="command", required=True)
    save = commands.add_parser("save")
    save.add_argument("--store", type=Path, required=True)
    save.add_argument("--result", type=Path, required=True)
    save.add_argument("--judgement", type=Path, required=True, help="The judge's answer.")
    save.add_argument("--side", type=Path, required=True, help="The checked judgement (runner.judge check).")
    save.add_argument("--used-by", action="append", default=[], help="A fixed score or try id that uses it. Repeat.")
    get = commands.add_parser("get")
    get.add_argument("--store", type=Path, required=True)
    get.add_argument("--lesson-url", required=True)
    get.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "save":
            print(save_lesson(args.store, args.result, args.judgement, args.side, args.used_by))
        else:
            target = get_lesson(args.store, args.lesson_url, args.out)
            print("\t".join(str(target / name) for name in (RESULT_FILE_NAME, STORED_ANSWER_FILE_NAME, STORED_SIDE_FILE_NAME)))
    except (OSError, ValidationError, ValueError) as error:
        print(f"Cannot {args.command} the lesson: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
