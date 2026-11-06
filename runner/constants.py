"""Fixed values the runner uses. Values copied from CollageAI say where they come from."""

from typing import Final

# Repo layout
EXPERIMENTS_DIR: Final[str] = "experiments"
EXPERIMENT_FILE_NAME: Final[str] = "experiment.yaml"
EXPERIMENT_FILES_DIR: Final[str] = "files"
# Keeps an empty files/ folder in git; never copied into CollageAI.
PLACEHOLDER_FILE_NAME: Final[str] = ".gitkeep"
TEST_SET_DIR: Final[str] = "test-set"
CASE_FILE_NAME: Final[str] = "case.yaml"
RESULT_FILE_NAME: Final[str] = "result.json"
DEFAULT_OUTPUT_DIR: Final[str] = "outputs"

# An experiment may only replace prompt code, never routes, services or database code.
EXPERIMENT_OVERRIDE_ROOT: Final[str] = "server/agents"
COLLAGE_SERVER_DIR: Final[str] = "server"

# Never copied out of the CollageAI server folder. ".env" stays out so a developer's
# local settings (which may point at a real database) never reach a run.
SERVER_COPY_IGNORE: Final[tuple[str, ...]] = (
    "venv", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".pytest-tmp", ".env", "*.pyc",
)

# Throwaway database
DEFAULT_MONGO_URI: Final[str] = "mongodb://localhost:27017"
MONGO_URI_ENV: Final[str] = "RUNNER_MONGO_URI"
RUN_DB_NAME_PREFIX: Final[str] = "prompt_eval_"
SECRET_BYTES: Final[int] = 32
# Settings CollageAI needs to boot. The runner makes fresh random values for every run.
GENERATED_SECRET_SETTINGS: Final[tuple[str, ...]] = ("SECRET_KEY", "JWT_SECRET_KEY")

# Lesson wizard routes, called the same way as client/src/api/lessons.ts.
LOGIN_PATH: Final[str] = "/api/auth/login"
WIZARD_BASE_PATH: Final[str] = "/api/courses/{course_id}/lessons/wizard"
UPLOAD_PATH: Final[str] = WIZARD_BASE_PATH + "/upload"
OBJECTIVES_PATH: Final[str] = WIZARD_BASE_PATH + "/learning-objectives"
CONCEPTS_PATH: Final[str] = WIZARD_BASE_PATH + "/concepts"
SCAFFOLD_PATH: Final[str] = WIZARD_BASE_PATH + "/scaffold"
CREATE_LESSON_PATH: Final[str] = WIZARD_BASE_PATH + "/generate"
STREAM_PATH: Final[str] = WIZARD_BASE_PATH + "/generate/{lesson_id}/stream"
TEXT_MATERIAL_SOURCE: Final[str] = "text"

# Website defaults, from client/src/pages/lesson-wizard-page.tsx (MAX_LO_COUNT, MAX_CONCEPT_COUNT)
# and the exercise type the page fills in when the plan leaves one empty.
WEBSITE_OBJECTIVE_COUNT: Final[int] = 5
WEBSITE_CONCEPT_COUNT: Final[int] = 10
WEBSITE_DEFAULT_EXERCISE_TYPE: Final[str] = "problem_set"

# Server-sent events (SSE) from the lesson stream route, see services/gen/lesson_wizard.py.
SSE_DATA_PREFIX: Final[str] = "data: "
SSE_EVENT_SEPARATOR: Final[str] = "\n\n"
SSE_DONE_MARKER: Final[str] = "[DONE]"
SSE_EVENT_TYPE_KEY: Final[str] = "type"
SSE_ERROR_EVENT_TYPE: Final[str] = "error"
