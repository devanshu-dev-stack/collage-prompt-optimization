"""Compare a baseline run (dev) with an experiment run (a preview), case by case.

Writes summary.json (read by the shared page) and comment.md (posted on the try's issue).
This compares structure only: counts, block types, objectives and timing. Judging quality
comes with the judge, once "better" is defined.

Usage:
    python -m runner.compare --baseline outputs/baseline --experiment outputs/try \\
        --target pr-2101 --commit <sha> --issue 12 --out results/12
"""

import argparse
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from runner.constants import COMMENT_FILE_NAME, QUIZ_BLOCK_TYPE, RESULT_FILE_NAME, SUMMARY_FILE_NAME
from runner.models import LessonRunResult
from runner.summary_models import (
    BlockDoc,
    CaseComparison,
    CaseSummary,
    ConceptDoc,
    ConceptSummary,
    ExerciseDoc,
    LessonDoc,
    ObjectiveDoc,
    RunSummary,
)


def _quiz_questions(blocks: list[BlockDoc]) -> int:
    return sum(len(block.questions) for block in blocks if block.type == QUIZ_BLOCK_TYPE)


def summarize_case(result: LessonRunResult) -> CaseSummary:
    lesson = LessonDoc.model_validate(result.lesson) if isinstance(result.lesson, dict) else LessonDoc()
    concept_types: Counter[str] = Counter()
    exercise_types: Counter[str] = Counter()
    concepts: list[ConceptSummary] = []
    for raw_concept in result.concepts:
        concept = ConceptDoc.model_validate(raw_concept)
        exercises = [ExerciseDoc.model_validate(raw) for raw in result.exercises_by_concept.get(concept.id, [])]
        exercise_blocks = [block for exercise in exercises for block in exercise.blocks]
        concept_types.update(block.type for block in concept.blocks)
        exercise_types.update(block.type for block in exercise_blocks)
        concepts.append(ConceptSummary(
            title=concept.title, block_types=dict(Counter(block.type for block in concept.blocks)),
            exercises=len(exercises), quiz_questions=_quiz_questions(exercise_blocks),
        ))
    return CaseSummary(
        finished=result.finished, failed_step=result.failed_step.value if result.failed_step else None,
        error=result.error, lesson_url=result.lesson_url, title=lesson.title,
        objectives=[item.text if isinstance(item, ObjectiveDoc) else item for item in lesson.learning_objectives],
        concepts=concepts, concept_block_types=dict(concept_types), exercise_block_types=dict(exercise_types),
        exercises=sum(concept.exercises for concept in concepts),
        quiz_questions=sum(concept.quiz_questions for concept in concepts),
        step_seconds={step.step.value: round(step.seconds, 1) for step in result.steps},
    )


def _load_cases(run_dir: Path) -> dict[str, CaseSummary]:
    results = (LessonRunResult.model_validate_json(path.read_text(encoding="utf-8"))
               for path in sorted(run_dir.glob(f"*/{RESULT_FILE_NAME}")))
    return {result.case_id: summarize_case(result) for result in results}


def _cell(summary: Optional[CaseSummary], value: str) -> str:
    return value if summary and summary.finished else "failed" if summary else "missing"


def _comment(summary: RunSummary) -> str:
    lines = [f"Results for `{summary.target}`" + (f" at `{summary.commit[:7]}`" if summary.commit else "") +
             ", compared with dev. Counts only; quality scoring comes with the judge.", ""]
    for case in summary.cases:
        base, test = case.baseline, case.experiment
        lines += [f"**{case.case_id}**", "", "| | dev | this try |", "|---|---|---|"]
        rows = [
            ("Objectives", lambda s: str(len(s.objectives))),
            ("Concepts", lambda s: str(len(s.concepts))),
            ("Concept blocks", lambda s: str(sum(s.concept_block_types.values()))),
            ("Exercises", lambda s: str(s.exercises)),
            ("Quiz questions", lambda s: str(s.quiz_questions)),
            ("Lesson", lambda s: f"[open]({s.lesson_url})" if s.lesson_url else "none"),
        ]
        for label, read in rows:
            lines.append(f"| {label} | {_cell(base, read(base) if base else '')} | {_cell(test, read(test) if test else '')} |")
        for name, side in (("dev", base), ("this try", test)):
            if side and not side.finished:
                lines.append(f"\n{name} failed at {side.failed_step}: {side.error}")
        lines.append("")
    return "\n".join(lines)


def build_summary(baseline_dir: Path, experiment_dir: Path, target: str, commit: Optional[str], issue: Optional[int]) -> RunSummary:
    baseline, experiment = _load_cases(baseline_dir), _load_cases(experiment_dir)
    cases = [CaseComparison(case_id=case_id, baseline=baseline.get(case_id), experiment=experiment.get(case_id))
             for case_id in sorted(baseline.keys() | experiment.keys())]
    return RunSummary(issue=issue, target=target, commit=commit, created_at=datetime.now(UTC).isoformat(), cases=cases)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare a dev run with an experiment run.")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--commit")
    parser.add_argument("--issue", type=int)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary = build_summary(args.baseline, args.experiment, args.target, args.commit, args.issue)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / SUMMARY_FILE_NAME).write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    (args.out / COMMENT_FILE_NAME).write_text(_comment(summary), encoding="utf-8")
    print(f"Wrote {args.out / SUMMARY_FILE_NAME} and {args.out / COMMENT_FILE_NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
