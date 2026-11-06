"""Build a private copy of the CollageAI server for one run.

Copy the server, swap in the experiment's prompt files, and point it at a throwaway
database. The CollageAI checkout itself is never changed.
"""

import importlib
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

from flask import Flask

from runner.constants import (
    COLLAGE_SERVER_DIR,
    EXPERIMENT_FILES_DIR,
    EXPERIMENT_OVERRIDE_ROOT,
    GENERATED_SECRET_SETTINGS,
    PLACEHOLDER_FILE_NAME,
    SECRET_BYTES,
    SERVER_COPY_IGNORE,
)
from runner.errors import RunnerInputError
from runner.loaders import require_inside

COLLAGE_APP_MODULE = "app"


def read_collage_ref(collage_dir: Path) -> str:
    """The exact CollageAI commit this run used, saved with every result."""
    result = subprocess.run(
        ["git", "-C", str(collage_dir), "rev-parse", "HEAD"], capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RunnerInputError(f"{collage_dir} is not a git checkout of CollageAI.")
    return result.stdout.strip()


def copy_server(collage_dir: Path, work_dir: Path) -> Path:
    source = collage_dir / COLLAGE_SERVER_DIR
    if not source.is_dir():
        raise RunnerInputError(f"No server folder in {collage_dir}.")
    target = work_dir / COLLAGE_SERVER_DIR
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(*SERVER_COPY_IGNORE), symlinks=True)
    return target


def apply_experiment(experiment_dir: Path, work_dir: Path) -> list[str]:
    """Copy the experiment's files over the server copy and return the paths it changed.

    A file may only replace one that already exists under server/agents, so a typo in a
    path fails the run instead of silently testing the baseline.
    """
    files_root = experiment_dir / EXPERIMENT_FILES_DIR
    allowed_root = work_dir / EXPERIMENT_OVERRIDE_ROOT
    changed: list[str] = []
    for source in sorted(files_root.rglob("*")):
        if source.is_dir() or source.name == PLACEHOLDER_FILE_NAME:
            continue
        if source.is_symlink():
            raise RunnerInputError(f"Links are not allowed in an experiment: {source}")
        relative = source.relative_to(files_root)
        target = require_inside(work_dir / relative, allowed_root, "A changed file")
        if not target.is_file():
            raise RunnerInputError(f"{relative} does not exist in CollageAI. Check the path.")
        shutil.copyfile(source, target)
        changed.append(relative.as_posix())
    return changed


def configure_environment(mongo_uri: str, db_name: str) -> None:
    """Settings CollageAI reads at import. Call before loading the app."""
    # GitHub turns a missing secret into an empty string, and CollageAI would read "" as a
    # real value (for example an empty model name). Removing it lets the default apply.
    for key in [key for key, value in os.environ.items() if value == ""]:
        del os.environ[key]
    os.environ["MONGO_URI"] = mongo_uri
    os.environ["DB_NAME"] = db_name
    # Fresh random values every run, so no real secret is ever needed or used.
    for key in GENERATED_SECRET_SETTINGS:
        os.environ[key] = secrets.token_hex(SECRET_BYTES)


def load_app(server_dir: Path, mongo_uri: str) -> Flask:
    """Import the real server/app.py from the copy, after checking the database is local."""
    sys.path.insert(0, str(server_dir))
    os.chdir(server_dir)
    # CollageAI's own seed safety check: only localhost on port 27017 is accepted.
    from scripts.db_seed.common import validate_local_dev_uri

    validate_local_dev_uri(mongo_uri)
    app_module = importlib.import_module(COLLAGE_APP_MODULE)
    flask_app = app_module.app
    if not isinstance(flask_app, Flask):
        raise RunnerInputError("server/app.py did not build a Flask app.")
    return flask_app
