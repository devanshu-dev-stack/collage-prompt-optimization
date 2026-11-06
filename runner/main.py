"""Run every test case through the real lesson pipeline for one experiment and save the results.

Usage (from the repo root):
    python -m runner --collage-dir ../CollageAI --experiment experiments/baseline
"""

import argparse
import os
import sys
import tempfile
import traceback
from datetime import UTC, datetime
from pathlib import Path

from runner.collage_env import apply_experiment, configure_environment, copy_server, load_app, read_collage_ref
from runner.constants import DEFAULT_MONGO_URI, DEFAULT_OUTPUT_DIR, MONGO_URI_ENV, RESULT_FILE_NAME, RUN_DB_NAME_PREFIX
from runner.errors import RunnerInputError, RunnerStepError
from runner.lesson_flow import run_lesson_case
from runner.loaders import check_case_against_collage, find_case_dirs, load_case, load_experiment, read_source_text
from runner.models import LessonCase, LessonRunResult
from runner.readback import read_lesson, read_token_usage
from runner.seed import SeededTeacher, seed_course, seed_teacher
from runner.wizard_client import WizardClient

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run test cases through the CollageAI lesson pipeline.")
    parser.add_argument("--collage-dir", type=Path, required=True, help="A git checkout of CollageAI.")
    parser.add_argument("--experiment", type=Path, required=True, help="An experiment folder, e.g. experiments/baseline.")
    parser.add_argument("--case", type=Path, action="append", default=[], help="A test case folder. Repeat for more. Default: all.")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / DEFAULT_OUTPUT_DIR, help="Where results are written.")
    return parser.parse_args()


def _run_one_case(
    client: WizardClient, teacher: SeededTeacher, case_dir: Path, case: LessonCase, result: LessonRunResult,
) -> None:
    course_id = seed_course(teacher, case)
    try:
        lesson_id = run_lesson_case(client, course_id, case, read_source_text(case_dir, case), result)
        result.lesson, result.concepts, result.exercises = read_lesson(teacher.org_id, lesson_id)
        result.finished = True
    except RunnerStepError as error:
        result.failed_step = error.step
        result.error = str(error)
    finally:
        result.token_usage = read_token_usage(teacher.org_id, course_id)


def run(args: argparse.Namespace) -> int:
    repo_root = REPO_ROOT
    collage_dir = args.collage_dir.resolve()
    experiment_dir = (repo_root / args.experiment).resolve()
    experiment = load_experiment(repo_root, experiment_dir)
    case_dirs = [(repo_root / c).resolve() for c in args.case] or find_case_dirs(repo_root)
    cases = [(case_dir, load_case(repo_root, case_dir)) for case_dir in case_dirs]
    if not cases:
        raise RunnerInputError("No test cases found.")
    collage_ref = read_collage_ref(collage_dir)
    out_dir = args.out.resolve() / experiment.name
    mongo_uri = os.environ.get(MONGO_URI_ENV, DEFAULT_MONGO_URI)
    db_name = RUN_DB_NAME_PREFIX + datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    with tempfile.TemporaryDirectory() as work:
        work_dir = Path(work)
        server_dir = copy_server(collage_dir, work_dir)
        changed_files = apply_experiment(experiment_dir, work_dir)
        configure_environment(mongo_uri, db_name)
        app = load_app(server_dir, mongo_uri)
        for _, case in cases:
            check_case_against_collage(case)
        teacher = seed_teacher()
        client = WizardClient(app)
        client.login(teacher.email, teacher.password)

        finished = 0
        for case_dir, case in cases:
            result = LessonRunResult(case_id=case.id, experiment=experiment.name, collage_ref=collage_ref,
                                     changed_files=changed_files, finished=False)
            _run_one_case(client, teacher, case_dir, case, result)
            case_out = out_dir / case.id
            case_out.mkdir(parents=True, exist_ok=True)
            (case_out / RESULT_FILE_NAME).write_text(result.model_dump_json(indent=2), encoding="utf-8")
            finished += int(result.finished)
            status = "finished" if result.finished else f"FAILED at {result.failed_step}: {result.error}"
            print(f"[{case.id}] {status} -> {case_out / RESULT_FILE_NAME}")

    print(f"{finished} of {len(cases)} case(s) finished. Database used: {db_name}")
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
