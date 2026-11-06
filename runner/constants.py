"""Fixed values the runner uses. Values copied from CollageAI say where they come from."""

import re
from typing import Final

# Repo layout
TEST_SET_DIR: Final[str] = "test-set"
CASE_FILE_NAME: Final[str] = "case.yaml"
RESULT_FILE_NAME: Final[str] = "result.json"
DEFAULT_OUTPUT_DIR: Final[str] = "outputs"

# Where the runner may send the test teacher's password. Anything else is refused.
# Preview address pattern from CollageAI's qa/README.md (Render's "-pr-<number>" previews).
PREVIEW_URL_TEMPLATE: Final[str] = "https://collageai-dev-pr-{pr_number}.onrender.com"
PREVIEW_HOST_PATTERN: Final[re.Pattern[str]] = re.compile(r"^collageai-dev-pr-\d+\.onrender\.com$")
DEV_TARGET_NAME: Final[str] = "dev"
PREVIEW_TARGET_PREFIX: Final[str] = "pr-"
REQUIRED_SCHEME: Final[str] = "https"

# Settings read from the environment (GitHub secrets / variables, or your shell). Never written to files.
DEV_URL_ENV: Final[str] = "RUNNER_DEV_URL"
TEACHER_EMAIL_ENV: Final[str] = "RUNNER_TEACHER_EMAIL"
TEACHER_PASSWORD_ENV: Final[str] = "RUNNER_TEACHER_PASSWORD"

# Login cookies, from CollageAI server/app.py (JWT_ACCESS_CSRF_COOKIE_NAME) and
# Flask-JWT-Extended's default header name, which app.py does not change.
CSRF_COOKIE_NAME: Final[str] = "collage_csrf_access_token"
CSRF_HEADER_NAME: Final[str] = "X-CSRF-TOKEN"

# Seconds. Content generation streams for minutes; the server sends heartbeats in between.
CONNECT_TIMEOUT_SECONDS: Final[float] = 30.0
READ_TIMEOUT_SECONDS: Final[float] = 300.0

# Routes, called the same way as client/src/api/*.ts.
LOGIN_PATH: Final[str] = "/api/auth/login"
COURSES_PATH: Final[str] = "/api/courses"
WIZARD_BASE_PATH: Final[str] = "/api/courses/{course_id}/lessons/wizard"
UPLOAD_PATH: Final[str] = WIZARD_BASE_PATH + "/upload"
OBJECTIVES_PATH: Final[str] = WIZARD_BASE_PATH + "/learning-objectives"
CONCEPTS_PATH: Final[str] = WIZARD_BASE_PATH + "/concepts"
SCAFFOLD_PATH: Final[str] = WIZARD_BASE_PATH + "/scaffold"
CREATE_LESSON_PATH: Final[str] = WIZARD_BASE_PATH + "/generate"
STREAM_PATH: Final[str] = WIZARD_BASE_PATH + "/generate/{lesson_id}/stream"
LESSON_PATH: Final[str] = "/api/courses/{course_id}/lessons/{lesson_id}"
LESSON_CONCEPTS_PATH: Final[str] = LESSON_PATH + "/concepts"
ASSESSMENTS_PATH: Final[str] = "/api/assessments"
# The lesson page in the browser, from client/src/utils/routes.ts (LESSON_DETAIL).
LESSON_PAGE_PATH: Final[str] = "/courses/{course_id}/lessons/{lesson_id}"

TEXT_MATERIAL_SOURCE: Final[str] = "text"
UPLOAD_MATERIAL_SOURCE: Final[str] = "upload"
UPLOAD_FILES_FIELD: Final[str] = "files"
# File types a test case may upload, as the wizard accepts them (server/utils/file_handling).
UPLOAD_MIME_TYPES: Final[dict[str, str]] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
EXERCISE_MODE: Final[str] = "exercise"
FORMATIVE_MODE: Final[str] = "formative"
# The lesson page asks for up to 100 concepts in one page (client/src/hooks/use-lesson-with-content.ts).
CONCEPTS_PAGE_LIMIT: Final[int] = 100
COURSES_PAGE_LIMIT: Final[int] = 100

# Website defaults, from client/src/pages/lesson-wizard-page.tsx (MAX_LO_COUNT, MAX_CONCEPT_COUNT)
# and the exercise type the page fills in when the plan leaves one empty.
WEBSITE_OBJECTIVE_COUNT: Final[int] = 5
WEBSITE_CONCEPT_COUNT: Final[int] = 10
WEBSITE_DEFAULT_EXERCISE_TYPE: Final[str] = "problem_set"

# Server-sent events (SSE) from the lesson stream route, see server/services/gen/lesson_wizard.py.
SSE_DATA_PREFIX: Final[str] = "data: "
SSE_DONE_MARKER: Final[str] = "[DONE]"
SSE_EVENT_TYPE_KEY: Final[str] = "type"
SSE_ERROR_EVENT_TYPE: Final[str] = "error"

COMMIT_SHA_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
# Ids the Prompt Lab page writes: try ids ("t" + milliseconds) and people's short names.
TRY_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^t\d{10,16}$")
AUTHOR_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9-]{1,28}$")

# A try request: an issue in this repo, opened by the relay once the preview runs the try's commit.
# Its body holds one JSON block.
TRY_JSON_BLOCK_PATTERN: Final[re.Pattern[str]] = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
# GitHub's author_association values for people who may start a run (it uses the test login).
TRUSTED_AUTHOR_ASSOCIATIONS: Final[frozenset[str]] = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})

# Comparison output, read by the shared page from the results branch.
SUMMARY_FILE_NAME: Final[str] = "summary.json"
COMMENT_FILE_NAME: Final[str] = "comment.md"
QUIZ_BLOCK_TYPE: Final[str] = "quiz"
