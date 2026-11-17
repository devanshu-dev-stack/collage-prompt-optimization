"""Keep every judged summative on the `lessons` branch too, in its own folder, so a check change re-judges it.

Usage:
    python -m runner.assessment_store save --store <folder> --result <result.json> \\
        --judgement <answer.json> --side <side.json> --used-by <baseline or try id> [--used-by ...]
    python -m runner.assessment_store get --store <folder> --summative-url <url> --out <folder>
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from runner.assessment_judge_models import AssessmentJudgement, AssessmentSide
from runner.assessment_models import AssessmentRunResult
from runner.constants import (
    LESSON_ID_PATTERN,
    LESSON_INDEX_FILE_NAME,
    RESULT_FILE_NAME,
    STORED_ANSWER_FILE_NAME,
    STORED_ASSESSMENTS_DIR,
    STORED_SIDE_FILE_NAME,
)
from runner.lesson_store import unpack_item_files, write_item_files


class StoredAssessment(BaseModel):
    summative_url: str
    case_id: str
    used_by: list[str] = Field(default_factory=list)
    saved_at: str


class AssessmentIndex(BaseModel):
    assessments: dict[str, StoredAssessment] = Field(default_factory=dict)


def _read_index(folder: Path) -> AssessmentIndex:
    path = folder / LESSON_INDEX_FILE_NAME
    return AssessmentIndex.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else AssessmentIndex()


def save_assessment(store: Path, result_path: Path, answer_path: Path, side_path: Path, used_by: list[str]) -> str:
    """Store one judged summative. Saving it again replaces its judgement and adds to `used_by`."""
    raw = result_path.read_bytes()
    result = AssessmentRunResult.model_validate_json(raw)
    if not result.finished or not result.summative_id or not result.summative_url:
        raise ValueError(f"{result_path} is not a finished summative.")
    # A summative id is a Mongo id too, so the lesson id rule keeps its folder name safe.
    if not LESSON_ID_PATTERN.fullmatch(result.summative_id):
        raise ValueError(f"{result_path} has an unexpected summative id.")
    AssessmentJudgement.model_validate_json(answer_path.read_text(encoding="utf-8"))
    AssessmentSide.model_validate_json(side_path.read_text(encoding="utf-8"))

    folder = store / STORED_ASSESSMENTS_DIR
    write_item_files(folder / result.summative_id, raw, answer_path, side_path)
    index = _read_index(folder)
    earlier = index.assessments.get(result.summative_id)
    index.assessments[result.summative_id] = StoredAssessment(
        summative_url=result.summative_url, case_id=result.case_id,
        used_by=sorted(set((earlier.used_by if earlier else []) + used_by)), saved_at=datetime.now(UTC).isoformat(),
    )
    index.assessments = dict(sorted(index.assessments.items()))
    (folder / LESSON_INDEX_FILE_NAME).write_text(index.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result.summative_id


def get_assessment(store: Path, summative_url: str, out: Path) -> Path:
    """Unpack a stored summative into `out/<summative id>/` and return that folder."""
    folder = store / STORED_ASSESSMENTS_DIR
    found = [item_id for item_id, item in _read_index(folder).assessments.items() if item.summative_url == summative_url]
    if not found:
        raise ValueError(f"No stored summative for {summative_url}.")
    return unpack_item_files(folder / found[0], out / found[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep judged summatives on the lessons branch, and get them back.")
    commands = parser.add_subparsers(dest="command", required=True)
    save = commands.add_parser("save")
    save.add_argument("--store", type=Path, required=True)
    save.add_argument("--result", type=Path, required=True)
    save.add_argument("--judgement", type=Path, required=True, help="The judge's answer.")
    save.add_argument("--side", type=Path, required=True, help="The checked judgement (runner.assessment_judge check).")
    save.add_argument("--used-by", action="append", default=[], help="A fixed score or try id that uses it. Repeat.")
    get = commands.add_parser("get")
    get.add_argument("--store", type=Path, required=True)
    get.add_argument("--summative-url", required=True)
    get.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "save":
            print(save_assessment(args.store, args.result, args.judgement, args.side, args.used_by))
        else:
            target = get_assessment(args.store, args.summative_url, args.out)
            print("\t".join(str(target / name) for name in (RESULT_FILE_NAME, STORED_ANSWER_FILE_NAME, STORED_SIDE_FILE_NAME)))
    except (OSError, ValidationError, ValueError) as error:
        print(f"Cannot {args.command} the summative: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
