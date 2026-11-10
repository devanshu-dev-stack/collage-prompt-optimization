"""A person's own material, as the Prompt Lab page saves it, checked against the lesson wizard's limits.

The closed lists copy CollageAI dev: subjects from server/utils/subject_categories.py, course levels
from server/constants/course.py, languages from client/src/constants/site-languages.ts.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from runner.constants import (
    ASSET_ID_PATTERN,
    MAX_COURSE_TITLE_CHARS,
    MAX_CUSTOM_INSTRUCTIONS_CHARS,
    MAX_OWN_FILE_BYTES,
    MAX_OWN_FILE_NAME_CHARS,
    MAX_OWN_FILES,
    MAX_OWN_TOTAL_BYTES,
)


class Subject(str, Enum):
    COMPUTER_SCIENCE = "computer_science"
    ENGINEERING = "engineering"
    MATHEMATICS = "mathematics"
    PHYSICAL_SCIENCES = "physical_sciences"
    LIFE_SCIENCES = "life_sciences"
    HEALTH_MEDICINE = "health_medicine"
    HUMANITIES = "humanities"
    SOCIAL_SCIENCES = "social_sciences"
    BUSINESS_MANAGEMENT = "business_management"
    ECONOMICS = "economics"
    ARTS_DESIGN = "arts_design"
    MUSIC = "music"
    EDUCATION = "education"
    LAW = "law"
    LANGUAGES = "languages"
    OTHER = "other"


class CourseLevel(str, Enum):
    GRADE_9 = "grade_9"
    GRADE_10 = "grade_10"
    GRADE_11 = "grade_11"
    GRADE_12 = "grade_12"
    INTRODUCTORY = "introductory"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    GRADUATE = "graduate"
    DOCTORATE = "doctorate"


class LessonLanguage(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"
    HEBREW = "he"
    ARABIC = "ar"


class OwnFileType(str, Enum):
    """The platform's file types the page can store. Word and PowerPoint files are saved as PDF first."""

    PDF = "application/pdf"
    TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    PNG = "image/png"
    JPEG = "image/jpeg"


OWN_FILE_EXTENSIONS: dict[OwnFileType, str] = {
    OwnFileType.PDF: ".pdf",
    OwnFileType.TEXT: ".txt",
    OwnFileType.MARKDOWN: ".md",
    OwnFileType.PNG: ".png",
    OwnFileType.JPEG: ".jpg",
}


class OwnFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    asset: str = Field(pattern=ASSET_ID_PATTERN)
    name: str = Field(min_length=1, max_length=MAX_OWN_FILE_NAME_CHARS)
    type: OwnFileType
    size: int = Field(ge=1, le=MAX_OWN_FILE_BYTES)


class OwnMaterial(BaseModel):
    """materials/<user id>/items/<material id> on the page. Extra fields (createdAt, handle) are ignored."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    title: str = Field(min_length=1, max_length=MAX_COURSE_TITLE_CHARS)
    subject: Subject
    level: CourseLevel
    language: LessonLanguage
    custom_instructions: Optional[str] = Field(default=None, alias="customInstructions",
                                               max_length=MAX_CUSTOM_INSTRUCTIONS_CHARS)
    files: list[OwnFile] = Field(min_length=1, max_length=MAX_OWN_FILES)

    @model_validator(mode="after")
    def _within_total_size(self) -> "OwnMaterial":
        total = sum(item.size for item in self.files)
        if total > MAX_OWN_TOTAL_BYTES:
            raise ValueError(f"The files add up to {total} bytes; the lesson wizard takes at most {MAX_OWN_TOTAL_BYTES}.")
        if len({item.asset for item in self.files}) != len(self.files):
            raise ValueError("The same file is listed twice.")
        return self
