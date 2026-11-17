"""Make one summative per test case on a CollageAI site and save each result.

Usage (from the repo root):
    python -m runner.assessment_runner --target dev --case test-set/chemistry-2e-ch1 --run-name dev-a1
"""

import argparse
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

from runner.api_client import CollageClient
from runner.assessment_flow import run_assessment_case
from runner.assessment_models import AssessmentRunResult, AssessmentStep
from runner.constants import DEFAULT_OUTPUT_DIR, RESULT_FILE_NAME, SUMMATIVE_PAGE_PATH
from runner.course_setup import find_or_create_course
from runner.errors import RunnerInputError, RunnerStepError
from runner.loaders import find_case_dirs, load_assessment, load_case
from runner.main import REPO_ROOT, RUN_STAMP_FORMAT, teacher_login
from runner.target import resolve_target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make a summative for each test case through a CollageAI site.")
    parser.add_argument("--target", required=True, help="'dev', or 'pr-<number>' for a pull request preview.")
    parser.add_argument("--case", type=Path, action="append", default=[], help="A test case folder. Repeat for more. Default: all.")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / DEFAULT_OUTPUT_DIR, help="Where results are written.")
    parser.add_argument("--run-name", help="Folder name for this run under --out. Default: assessment-<target>-<time>.")
    return parser.parse_args()


def run(args: argparse.Namespace) -> int:
    target = resolve_target(args.target)
    email, password = teacher_login()
    case_dirs = [(REPO_ROOT / c).resolve() for c in args.case] or find_case_dirs(REPO_ROOT)
    cases = [(case_dir, load_case(REPO_ROOT, case_dir), load_assessment(REPO_ROOT, case_dir)) for case_dir in case_dirs]
    if not cases:
        raise RunnerInputError("No test cases found.")
    run_name = args.run_name or f"assessment-{target.name}-{datetime.now(UTC).strftime(RUN_STAMP_FORMAT)}"
    run_dir = args.out.resolve() / run_name

    client = CollageClient(target.base_url)
    client.login(email, password)
    finished = 0
    for case_dir, case, assessment in cases:
        result = AssessmentRunResult(case_id=case.id, target=target.name, base_url=target.base_url,
                                     started_at=datetime.now(UTC).isoformat(), objectives=assessment.objectives,
                                     questions_asked=assessment.question_count)
        try:
            # find_or_create_course reports its failures as a lesson step; here it is the course step.
            try:
                result.course_id = find_or_create_course(client, case)
            except RunnerStepError as error:
                raise RunnerStepError(str(error), AssessmentStep.COURSE) from error
            result.summative_id = run_assessment_case(client, result.course_id, case, assessment, case_dir, result)
            result.summative_url = target.base_url + SUMMATIVE_PAGE_PATH.format(
                course_id=result.course_id, summative_id=result.summative_id)
            result.finished = True
        except RunnerStepError as error:
            result.failed_step = error.step if isinstance(error.step, AssessmentStep) else None
            result.error = str(error)
        case_out = run_dir / case.id
        case_out.mkdir(parents=True, exist_ok=True)
        (case_out / RESULT_FILE_NAME).write_text(result.model_dump_json(indent=2), encoding="utf-8")
        finished += int(result.finished)
        print(f"[{case.id}] " + ("finished" if result.finished else f"FAILED at {result.failed_step}: {result.error}"))
        if result.summative_url:
            print(f"  summative page: {result.summative_url}")

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


if __name__ == "__main__":
    sys.exit(main())
