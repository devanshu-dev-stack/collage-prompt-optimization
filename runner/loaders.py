"""Read experiments and test cases from disk, and reject anything ambiguous before a run starts."""

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

from runner.constants import CASE_FILE_NAME, EXPERIMENT_FILE_NAME, EXPERIMENTS_DIR, TEST_SET_DIR
from runner.errors import RunnerInputError
from runner.models import ExperimentSpec, LessonCase

ModelT = TypeVar("ModelT", bound=BaseModel)


def _parse(model: type[ModelT], path: Path) -> ModelT:
    if not path.is_file():
        raise RunnerInputError(f"Missing file: {path}")
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise RunnerInputError(f"{path} must hold key: value pairs.")
    return model.model_validate(raw)


def require_inside(child: Path, parent: Path, label: str) -> Path:
    """Resolve child and make sure it sits inside parent (blocks '..' and links that point away)."""
    resolved = child.resolve()
    if not resolved.is_relative_to(parent.resolve()):
        raise RunnerInputError(f"{label} must be inside {parent}: {child}")
    return resolved


def load_experiment(repo_root: Path, experiment_dir: Path) -> ExperimentSpec:
    folder = require_inside(experiment_dir, repo_root / EXPERIMENTS_DIR, "Experiment folder")
    return _parse(ExperimentSpec, folder / EXPERIMENT_FILE_NAME)


def find_case_dirs(repo_root: Path) -> list[Path]:
    return sorted(path.parent for path in (repo_root / TEST_SET_DIR).glob(f"*/{CASE_FILE_NAME}"))


def load_case(repo_root: Path, case_dir: Path) -> LessonCase:
    folder = require_inside(case_dir, repo_root / TEST_SET_DIR, "Test case folder")
    case = _parse(LessonCase, folder / CASE_FILE_NAME)
    require_inside(folder / case.source_file, folder, "source_file")
    return case


def read_source_text(case_dir: Path, case: LessonCase) -> str:
    return (case_dir / case.source_file).read_text(encoding="utf-8")


def check_case_against_collage(case: LessonCase) -> None:
    """Use CollageAI's own lists, so a typo fails here instead of quietly becoming another subject."""
    from constants.course import COURSE_DIFFICULTY_LEVELS
    from utils.languages import Languages
    from utils.subject_categories import SUBJECT_TO_CATEGORY

    if case.subject not in SUBJECT_TO_CATEGORY:
        raise RunnerInputError(f"Case {case.id}: unknown subject '{case.subject}'. Use one of: {sorted(SUBJECT_TO_CATEGORY)}")
    if case.difficulty not in COURSE_DIFFICULTY_LEVELS:
        raise RunnerInputError(f"Case {case.id}: unknown difficulty '{case.difficulty}'. Use one of: {sorted(COURSE_DIFFICULTY_LEVELS)}")
    allowed_languages = {language.value for language in Languages}
    if case.language not in allowed_languages:
        raise RunnerInputError(f"Case {case.id}: unknown language '{case.language}'. Use one of: {sorted(allowed_languages)}")
