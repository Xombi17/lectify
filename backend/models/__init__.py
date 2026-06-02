"""Lectify backend models — re-exports for convenient imports."""

# Existing entity models
from .user import UserCreate, UserDB, UserLogin, UserPublic, AuthResponse
from .lecture import (
    LectureCreate,
    LectureDB,
    LectureSummary,
    LectureStatus,
    StudyMaterials,
    QuizQuestion,
    QuizAttempt,
    QuizResult,
    Flashcard,
)
from .bookmark import BookmarkCreate, BookmarkDB, BookmarkPublic
from .chat import ChatMessageCreate, ChatMessageDB, ChatMessagePublic
from .attempt import QuizAttemptCreate, QuizAttemptDB, QuizAttemptPublic
from .flashcard_review import (
    FlashcardReviewCreate,
    FlashcardReviewDB,
    FlashcardReviewPublic,
)

# Academic hierarchy (Phase A.1)
from .academic import (
    InstitutionCreate, InstitutionDB, InstitutionPublic,
    YearCreate, YearDB, YearPublic,
    BranchCreate, BranchDB, BranchPublic,
    SemesterCreate, SemesterDB, SemesterPublic,
    SubjectCreate, SubjectDB, SubjectPublic,
    DivisionCreate, DivisionDB, DivisionPublic,
    ClassCreate, ClassDB, ClassPublic,
    TeacherAssignmentCreate, TeacherAssignmentDB, TeacherAssignmentPublic,
    StudentEnrollmentCreate, StudentEnrollmentDB, StudentEnrollmentPublic,
)

__all__ = [
    # user
    "UserCreate", "UserDB", "UserLogin", "UserPublic", "AuthResponse",
    # lecture
    "LectureCreate", "LectureDB", "LectureSummary", "LectureStatus",
    "StudyMaterials", "QuizQuestion", "QuizAttempt", "QuizResult", "Flashcard",
    # bookmarks
    "BookmarkCreate", "BookmarkDB", "BookmarkPublic",
    # chat
    "ChatMessageCreate", "ChatMessageDB", "ChatMessagePublic",
    # attempts
    "QuizAttemptCreate", "QuizAttemptDB", "QuizAttemptPublic",
    # flashcard reviews
    "FlashcardReviewCreate", "FlashcardReviewDB", "FlashcardReviewPublic",
    # academic hierarchy
    "InstitutionCreate", "InstitutionDB", "InstitutionPublic",
    "YearCreate", "YearDB", "YearPublic",
    "BranchCreate", "BranchDB", "BranchPublic",
    "SemesterCreate", "SemesterDB", "SemesterPublic",
    "SubjectCreate", "SubjectDB", "SubjectPublic",
    "DivisionCreate", "DivisionDB", "DivisionPublic",
    "ClassCreate", "ClassDB", "ClassPublic",
    "TeacherAssignmentCreate", "TeacherAssignmentDB", "TeacherAssignmentPublic",
    "StudentEnrollmentCreate", "StudentEnrollmentDB", "StudentEnrollmentPublic",
]
