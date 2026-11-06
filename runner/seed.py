"""Create the teacher and one course per test case in the throwaway database.

Reuses CollageAI's own local seed helpers (server/scripts/db_seed), so the documents
have the same shape as the ones developers log in with locally.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from bson import ObjectId

from runner.errors import RunnerInputError
from runner.models import LessonCase

COURSE_TITLE_PREFIX = "Prompt eval: "


@dataclass(frozen=True)
class SeededTeacher:
    org_id: ObjectId
    faculty_id: ObjectId
    student_id: ObjectId
    email: str
    password: str


def seed_teacher() -> SeededTeacher:
    from db.db_manager import get_db_manager
    from db.seed_data import ensure_default_org
    from scripts.db_seed.common import FACULTY_EMAIL, FACULTY_PASSWORD
    from scripts.db_seed.users_seed import seed_users

    org_id = ensure_default_org()
    if not org_id:
        raise RunnerInputError("Could not create the organization in the throwaway database.")
    database = get_db_manager().get_database()
    faculty_id, student_id = seed_users(database["users"], ObjectId(org_id), datetime.now(UTC))
    return SeededTeacher(ObjectId(org_id), faculty_id, student_id, FACULTY_EMAIL, FACULTY_PASSWORD)


def seed_course(teacher: SeededTeacher, case: LessonCase) -> str:
    """One course per case, with the case's subject and level, taught by the seeded teacher."""
    from db.db_manager import get_db_manager
    from scripts.db_seed.courses_seed import seed_courses
    from scripts.db_seed.enrollments_seed import seed_course_enrollments

    database = get_db_manager().get_database()
    now = datetime.now(UTC)
    course_spec = {
        "title": COURSE_TITLE_PREFIX + case.course_title,
        "description": case.course_title,
        "params": {"subject": case.subject, "difficulty": case.difficulty},
    }
    seeded = seed_courses(
        database["courses"], teacher.org_id, [course_spec], now, teacher.faculty_id, database["subjects"],
    )
    course_id = seeded[0]["course_id"]
    seed_course_enrollments(
        enrollments_collection=database["enrollments"],
        org_id=teacher.org_id,
        course_id=course_id,
        faculty_id=teacher.faculty_id,
        student_id=teacher.student_id,
        now=now,
    )
    return str(course_id)
