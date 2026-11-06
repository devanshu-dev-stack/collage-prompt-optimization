"""Fix a version's score: several lessons made with its own prompts, each judged once.

Every try is then compared with these same runs instead of a new lesson made next to it, so
all tries meet the same yardstick (RELAY.md, "Fixed scores").

Usage:
    python -m runner.baseline --base dev --commit <sha> \\
        --run <result.json> <side.json> --run <result.json> <side.json> --out baseline.json
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from runner.compare import summarize_case
from runner.constants import COMMIT_SHA_PATTERN
from runner.judge_models import Baseline, BaselineCase, BaselineRun, PromptBase, SideJudgement
from runner.models import LessonRunResult


def build_baseline(base: PromptBase, commit: str, runs: list[tuple[Path, Path]]) -> Baseline:
    """Group (result.json, judged side) pairs by test case. Every lesson must have finished."""
    if not COMMIT_SHA_PATTERN.fullmatch(commit):
        raise ValueError(f"Not a full commit sha: {commit}")
    by_case: dict[str, list[BaselineRun]] = {}
    for result_path, side_path in runs:
        result = LessonRunResult.model_validate_json(result_path.read_text(encoding="utf-8"))
        if not result.finished:
            raise ValueError(f"{result_path} did not finish, so it cannot be part of a fixed score.")
        side = SideJudgement.model_validate_json(side_path.read_text(encoding="utf-8"))
        by_case.setdefault(result.case_id, []).append(BaselineRun(summary=summarize_case(result), judgement=side))
    return Baseline(base=base, commit=commit, made_at=datetime.now(UTC).isoformat(),
                    cases=[BaselineCase(case_id=case_id, runs=items) for case_id, items in sorted(by_case.items())])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a version's fixed score from judged lessons.")
    parser.add_argument("--base", type=PromptBase, choices=list(PromptBase), required=True)
    parser.add_argument("--commit", required=True, help="The full commit sha whose prompts made the lessons.")
    parser.add_argument("--run", nargs=2, type=Path, action="append", required=True, metavar=("RESULT", "SIDE"),
                        help="A lesson's result.json and its checked judgement. Repeat for each lesson.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        baseline = build_baseline(args.base, args.commit, [(result, side) for result, side in args.run])
    except (ValidationError, ValueError) as error:
        print(f"Cannot build the fixed score: {error}", file=sys.stderr)
        return 2
    args.out.write_text(baseline.model_dump_json(indent=2), encoding="utf-8")
    print(f"Wrote {args.out}: " + ", ".join(f"{case.case_id} from {len(case.runs)} lesson(s)" for case in baseline.cases))
    return 0


if __name__ == "__main__":
    sys.exit(main())
