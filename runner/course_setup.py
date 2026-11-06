"""One course per test case, owned by the test teacher. Reused across runs so dev does not fill up with courses."""

from runner.api_client import CollageClient
from runner.constants import COURSES_PAGE_LIMIT, COURSES_PATH
from runner.models import CoursesReply, CreatedCourseReply, LessonCase, LessonStep
from runner.replies import check_reply

COURSE_TITLE_PREFIX = "Prompt eval: "
# GET is served at "/api/courses/". Asking for it directly avoids a redirect that could drop to http.
COURSES_LIST_PATH = COURSES_PATH + "/"


def find_or_create_course(client: CollageClient, case: LessonCase) -> str:
    title = COURSE_TITLE_PREFIX + case.course_title
    listing = client.get(COURSES_LIST_PATH, {"page": "1", "limit": str(COURSES_PAGE_LIMIT)})
    courses = check_reply(listing, CoursesReply, LessonStep.COURSE, "Listing courses")
    for course in courses.data.items:
        if course.title == title:
            return course.id

    created = client.post_json(COURSES_PATH, {
        "title": title, "description": case.course_title, "subject": case.subject, "difficulty": case.difficulty,
    })
    return check_reply(created, CreatedCourseReply, LessonStep.COURSE, "Creating the course").data.id
