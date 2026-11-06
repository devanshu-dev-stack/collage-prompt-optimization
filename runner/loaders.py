"""Read test cases from disk, and reject anything ambiguous before a run starts."""

from pathlib import Path

import yaml

from runner.constants import CASE_FILE_NAME, TEST_SET_DIR
from runner.errors import RunnerInputError
from runner.models import LessonCase


def require_inside(child: Path, parent: Path, label: str) -> Path:
    """Resolve child and make sure it sits inside parent (blocks '..' and links that point away)."""
    resolved = child.resolve()
    if not resolved.is_relative_to(parent.resolve()):
        raise RunnerInputError(f"{label} must be inside {parent}: {child}")
    return resolved


def find_case_dirs(repo_root: Path) -> list[Path]:
    return sorted(path.parent for path in (repo_root / TEST_SET_DIR).glob(f"*/{CASE_FILE_NAME}"))


def load_case(repo_root: Path, case_dir: Path) -> LessonCase:
    folder = require_inside(case_dir, repo_root / TEST_SET_DIR, "Test case folder")
    case_file = folder / CASE_FILE_NAME
    if not case_file.is_file():
        raise RunnerInputError(f"Missing file: {case_file}")
    with case_file.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise RunnerInputError(f"{case_file} must hold key: value pairs.")
    case = LessonCase.model_validate(raw)
    require_inside(folder / case.source_file, folder, "source_file")
    return case


def read_source_text(case_dir: Path, case: LessonCase) -> str:
    return (case_dir / case.source_file).read_text(encoding="utf-8")
