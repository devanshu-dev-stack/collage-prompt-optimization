"""Build a test case from a person's own material on the Prompt Lab page, under the platform's limits.

Claude first saves the material document as JSON and downloads each of its files by asset id
(RELAY.md, "Own material"). This checks everything again, because the page's checks run in a
browser anyone can change, then writes test-set/own-<material id>/, which git ignores.

Usage:
    python -m runner.material build --material <material.json> --files <download folder> --id <material id>
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from runner.constants import (
    CASE_FILE_NAME,
    FILE_SIGNATURES,
    MATERIAL_ID_PATTERN,
    MAX_OWN_PDF_PAGES_TOTAL,
    OWN_CASE_PREFIX,
    PDF_PAGES_PATTERN,
    PDF_SUFFIX,
    PDF_TOOL_TIMEOUT_SECONDS,
    SAFE_NAME_FALLBACK,
    SAFE_NAME_MAX_CHARS,
    TEST_SET_DIR,
    TEXT_SOURCE_SUFFIXES,
)
from runner.errors import RunnerInputError
from runner.judge import SOURCE_TEXT_SUFFIX
from runner.loaders import load_case, require_inside
from runner.material_models import OWN_FILE_EXTENSIONS, OwnFile, OwnMaterial

REPO_ROOT = Path(__file__).resolve().parent.parent


def safe_name(name: str) -> str:
    """Lowercase letters and digits from a file's name, joined by dashes, so no name can escape its folder."""
    stem = name.rsplit(".", 1)[0].lower()
    words = re.findall(r"[a-z0-9]+", stem)
    return "-".join(words)[:SAFE_NAME_MAX_CHARS].strip("-") or SAFE_NAME_FALLBACK


def _downloaded(files_dir: Path, item: OwnFile) -> Path:
    """The one downloaded file named after the asset id (the download adds an extension)."""
    matches = [path for path in files_dir.iterdir() if path.is_file() and path.name.split(".", 1)[0] == item.asset]
    if len(matches) != 1:
        raise RunnerInputError(f"Expected one downloaded file for {item.name} (asset {item.asset}), found {len(matches)}.")
    return matches[0]


def _check_content(item: OwnFile, extension: str, data: bytes) -> None:
    if len(data) != item.size:
        raise RunnerInputError(f"{item.name}: the page says {item.size} bytes but the file has {len(data)}.")
    if extension in TEXT_SOURCE_SUFFIXES:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise RunnerInputError(f"{item.name}: a text file must be UTF-8.") from error
    elif not data.startswith(FILE_SIGNATURES[extension]):
        raise RunnerInputError(f"{item.name}: the file is not a real {extension} file.")


def _run_pdf_tool(args: list[str], label: str) -> str:
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=PDF_TOOL_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired as error:
        raise RunnerInputError(f"{label}: reading the PDF took too long.") from error
    if done.returncode != 0:
        raise RunnerInputError(f"{label}: the PDF could not be read.")
    return done.stdout


def _pdf_pages(path: Path, label: str) -> int:
    match = PDF_PAGES_PATTERN.search(_run_pdf_tool(["pdfinfo", str(path)], label))
    if not match:
        raise RunnerInputError(f"{label}: the PDF's page count could not be read.")
    return int(match.group(1))


def build_case(material: OwnMaterial, material_id: str, files_dir: Path, repo_root: Path = REPO_ROOT) -> Path:
    """Write the case folder: each file under a safe name, its text next to it for the judge, and case.yaml."""
    if not MATERIAL_ID_PATTERN.fullmatch(material_id):
        raise RunnerInputError(f"Not a material id: {material_id}")
    test_set = repo_root / TEST_SET_DIR
    case_dir = require_inside(test_set / f"{OWN_CASE_PREFIX}{material_id}", test_set, "Own material folder")
    if case_dir.exists():
        raise RunnerInputError(f"{case_dir} already exists. Material does not change, so reuse it.")
    case_dir.mkdir(parents=True)
    try:
        _write_case(material, material_id, files_dir, repo_root, case_dir)
    except Exception:
        # A half-built folder would block the next try at this material, so it goes.
        shutil.rmtree(case_dir)
        raise
    return case_dir


def _write_case(material: OwnMaterial, material_id: str, files_dir: Path, repo_root: Path, case_dir: Path) -> None:
    names: list[str] = []
    pages = 0
    for number, item in enumerate(material.files, start=1):
        extension = OWN_FILE_EXTENSIONS[item.type]
        data = _downloaded(files_dir, item).read_bytes()
        _check_content(item, extension, data)
        name = f"{number:02d}-{safe_name(item.name)}{extension}"
        target = case_dir / name
        target.write_bytes(data)
        text_file = case_dir / (name + SOURCE_TEXT_SUFFIX)
        if extension == PDF_SUFFIX:
            pages += _pdf_pages(target, item.name)
            if pages > MAX_OWN_PDF_PAGES_TOTAL:
                raise RunnerInputError(f"The PDFs have more than {MAX_OWN_PDF_PAGES_TOTAL} pages in total, the lesson wizard's limit.")
            text_file.write_text(_run_pdf_tool(["pdftotext", str(target), "-"], item.name), encoding="utf-8")
        elif extension in TEXT_SOURCE_SUFFIXES:
            text_file.write_text(data.decode("utf-8"), encoding="utf-8")
        names.append(name)
    case = {
        "id": f"{OWN_CASE_PREFIX}{material_id}",
        "course_title": material.title,
        "subject": material.subject.value,
        "difficulty": material.level.value,
        "language": material.language.value,
        "source_files": names,
        "custom_instructions": material.custom_instructions or None,
    }
    (case_dir / CASE_FILE_NAME).write_text(yaml.safe_dump(case, allow_unicode=True, sort_keys=False), encoding="utf-8")
    load_case(repo_root, case_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a test case from a person's own material.")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--material", type=Path, required=True, help="The material document's data, as JSON.")
    build.add_argument("--files", type=Path, required=True, help="Folder holding the files downloaded by asset id.")
    build.add_argument("--id", required=True, help="The material id, for example m1794350000000.")
    args = parser.parse_args()
    try:
        material = OwnMaterial.model_validate_json(args.material.read_text(encoding="utf-8"))
        case_dir = build_case(material, args.id, args.files)
    except ValidationError as error:
        problems = "; ".join(f"{'.'.join(str(p) for p in e['loc']) or 'material'}: {e['msg']}" for e in error.errors())
        print(f"Not accepted: {problems}", file=sys.stderr)
        return 1
    except RunnerInputError as error:
        print(f"Not accepted: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {case_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
