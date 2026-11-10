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
# File types a test case may upload, as the wizard accepts them (SUPPORTED_EXTENSIONS in
# server/utils/file_handling/helpers/constants.py).
UPLOAD_MIME_TYPES: Final[dict[str, str]] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
# Sources the judge sees as pictures: they have no text to read, so it opens the image itself.
IMAGE_SOURCE_SUFFIXES: Final[frozenset[str]] = frozenset({".png", ".jpg", ".jpeg"})
TEXT_SOURCE_SUFFIXES: Final[frozenset[str]] = frozenset({".txt", ".md"})
PDF_SUFFIX: Final[str] = ".pdf"

# A person's own material from the Prompt Lab page, held to the lesson wizard's limits on CollageAI dev.
# The test case is built in test-set/own-<material id>/, which git ignores: course material never
# goes into a repo.
OWN_CASE_PREFIX: Final[str] = "own-"
MATERIAL_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^m\d{10,16}$")
# The page stores each file as an artifact asset; this is the id format the asset store gives.
ASSET_ID_PATTERN: Final[str] = r"^[0-9a-f]{32}$"
MAX_OWN_FILES: Final[int] = 10  # MAX_WIZARD_UPLOAD_FILES, server/constants/lesson_wizard/upload.py
MAX_OWN_TOTAL_BYTES: Final[int] = 100 * 1024 * 1024  # MAX_WIZARD_UPLOAD_TOTAL_BYTES, same file
# The platform allows 100 MB per file, but the page's asset store takes at most 20 MiB per file.
MAX_OWN_FILE_BYTES: Final[int] = 20 * 1024 * 1024
MAX_OWN_PDF_PAGES_TOTAL: Final[int] = 1_000  # MAX_MULTIMODAL_ATTACHMENT_PAGES_TOTAL, same file
MAX_CUSTOM_INSTRUCTIONS_CHARS: Final[int] = 4_000  # CUSTOM_INSTRUCTIONS_MAX_LENGTH, server/constants/source_content.py
MAX_COURSE_TITLE_CHARS: Final[int] = 255  # COURSE_TITLE_MAX_LENGTH, client/src/utils/constants.ts
MAX_OWN_FILE_NAME_CHARS: Final[int] = 200
# Files are saved as "<number>-<safe name><extension>"; the safe name keeps only a-z and 0-9 runs.
SAFE_NAME_MAX_CHARS: Final[int] = 60
SAFE_NAME_FALLBACK: Final[str] = "file"
# Each file's first bytes must match its type, so a renamed file cannot pass as another type.
FILE_SIGNATURES: Final[dict[str, tuple[bytes, ...]]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
}
# pdftotext and pdfinfo (poppler) read PDFs; a stuck one is stopped after this many seconds.
PDF_TOOL_TIMEOUT_SECONDS: Final[int] = 120
PDF_PAGES_PATTERN: Final[re.Pattern[str]] = re.compile(r"^Pages:\s+(\d+)\s*$", re.MULTILINE)
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
