"""Run every test case through a CollageAI site (dev or a pull request preview) and save the results.

Usage (from the repo root):
    python -m runner --target pr-2101
    python -m runner --target dev --case test-set/biology-photosynthesis
    python -m runner --target pr-2101 --run-name try
"""

import argparse
import os
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

from runner.api_client import CollageClient
from runner.constants import DEFAULT_OUTPUT_DIR, LESSON_PAGE_PATH, RESULT_FILE_NAME, TEACHER_EMAIL_ENV, TEACHER_PASSWORD_ENV
from runner.course_setup import find_or_create_course
from runner.errors import RunnerInputError, RunnerStepError
from runner.lesson_flow import run_lesson_case
from runner.lesson_reader import read_lesson
from runner.loaders import find_case_dirs, load_case, read_source_text
from runner.models import LessonCase, LessonRunResult
from runner.target import Target, resolve_target

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_STAMP_FORMAT = "%Y%m%d-%H%M%S"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run test cases through a CollageAI site's lesson pipeline.")
    parser.add_argument("--target", required=True, help="'dev', or 'pr-<number>' for a pull request preview.")
    parser.add_argument("--case", type=Path, action="append", default=[], help="A test case folder. Repeat for more. Default: all.")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / DEFAULT_OUTPUT_DIR, help="Where results are written.")
    parser.add_argument("--run-name", help="Folder name for this run under --out. Default: <target>-<time>.")
    return parser.parse_args()


def _teacher_login() -> tuple[str, str]:
    email = os.environ.get(TEACHER_EMAIL_ENV, "")
    password = os.environ.get(TEACHER_PASSWORD_ENV, "")
    if not email or not password:
        raise RunnerInputError(f"Set {TEACHER_EMAIL_ENV} and {TEACHER_PASSWORD_ENV} to the test teacher's login.")
    return email, password


def _run_one_case(client: CollageClient, target: Target, case_dir: Path, case: LessonCase) -> LessonRunResult:
    result = LessonRunResult(case_id=case.id, target=target.name, base_url=target.base_url,
                             started_at=datetime.now(UTC).isoformat())
    try:
        course_id = find_or_create_course(client, case)
        result.course_id = course_id
        lesson_id = run_lesson_case(client, course_id, case, read_source_text(case_dir, case), result)
        # Teammates can open this page (logged in as the test teacher) to see the lesson as a teacher would.
        result.lesson_url = target.base_url + LESSON_PAGE_PATH.format(course_id=course_id, lesson_id=lesson_id)
        read_lesson(client, course_id, lesson_id, result)
        result.finished = True
    except RunnerStepError as error:
        result.failed_step = error.step
        result.error = str(error)
    return result


def run(args: argparse.Namespace) -> int:
    target = resolve_target(args.target)
    email, password = _teacher_login()
    case_dirs = [(REPO_ROOT / c).resolve() for c in args.case] or find_case_dirs(REPO_ROOT)
    cases = [(case_dir, load_case(REPO_ROOT, case_dir)) for case_dir in case_dirs]
    if not cases:
        raise RunnerInputError("No test cases found.")
    run_name = args.run_name or f"{target.name}-{datetime.now(UTC).strftime(RUN_STAMP_FORMAT)}"
    run_dir = args.out.resolve() / run_name

    client = CollageClient(target.base_url)
    client.login(email, password)
    finished = 0
    for case_dir, case in cases:
        result = _run_one_case(client, target, case_dir, case)
        case_out = run_dir / case.id
        case_out.mkdir(parents=True, exist_ok=True)
        (case_out / RESULT_FILE_NAME).write_text(result.model_dump_json(indent=2), encoding="utf-8")
        finished += int(result.finished)
        status = "finished" if result.finished else f"FAILED at {result.failed_step}: {result.error}"
        print(f"[{case.id}] {status}")
        if result.lesson_url:
            print(f"  lesson page: {result.lesson_url}")

    print(f"{finished} of {len(cases)} case(s) finished. Results: {run_dir}")
    return 0 if finished == len(cases) else 1


def main() -> int:
    try:
        return run(parse_args())
    except (RunnerInputError, RunnerStepError) as error:
        print(f"Run stopped: {error}", file=sys.stderr)
        return 2
    except Exception:
        traceback.print_exc()
        return 3
