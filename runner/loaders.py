"""Read test cases from disk, and reject anything ambiguous before a run starts."""

from pathlib import Path

import yaml

from runner.constants import CASE_FILE_NAME, OWN_CASE_PREFIX, TEST_SET_DIR, UPLOAD_MIME_TYPES
from runner.errors import RunnerInputError
from runner.models import LessonCase


def require_inside(child: Path, parent: Path, label: str) -> Path:
    """Resolve child and make sure it sits inside parent (blocks '..' and links that point away)."""
    resolved = child.resolve()
    if not resolved.is_relative_to(parent.resolve()):
        raise RunnerInputError(f"{label} must be inside {parent}: {child}")
    return resolved


def find_case_dirs(repo_root: Path) -> list[Path]:
    """The shared test cases. A person's own material runs only when named with --case."""
    return sorted(path.parent for path in (repo_root / TEST_SET_DIR).glob(f"*/{CASE_FILE_NAME}")
                  if not path.parent.name.startswith(OWN_CASE_PREFIX))


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
    for name in [case.source_file] if case.source_file else case.source_files:
        path = require_inside(folder / name, folder, "A source file")
        if not path.is_file():
            raise RunnerInputError(f"Missing source file: {path}")
        if case.source_files and path.suffix.lower() not in UPLOAD_MIME_TYPES:
            raise RunnerInputError(f"{name}: only {', '.join(UPLOAD_MIME_TYPES)} files can be uploaded.")
    return case


def read_source_text(case_dir: Path, case: LessonCase) -> str:
    return (case_dir / (case.source_file or "")).read_text(encoding="utf-8")


def read_source_files(case_dir: Path, case: LessonCase) -> list[tuple[str, bytes, str]]:
    """(file name, bytes, media type) for each file to upload, in the order the case lists them."""
    return [(name, (case_dir / name).read_bytes(), UPLOAD_MIME_TYPES[Path(name).suffix.lower()]) for name in case.source_files]
