import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user_optional, require_admin, require_teacher_or_admin
from app.db.session import get_db
from app.models.education import Chapter, Course, EducationLevel, ExamBoard, Lesson, Subject, Topic
from app.models.user import User, UserRole
from app.schemas.education import (
    ChapterCreate,
    ChapterResponse,
    CourseCreate,
    CourseDetail,
    CourseResponse,
    CourseUpdate,
    EducationLevelCreate,
    EducationLevelResponse,
    ExamBoardCreate,
    ExamBoardResponse,
    LessonCreate,
    LessonResponse,
    SubjectCreate,
    SubjectDetail,
    SubjectResponse,
    TopicCreate,
    TopicResponse,
)
from app.services.education_service import (
    assert_can_manage_chapter,
    assert_can_manage_course,
    assert_can_manage_subject,
    assert_can_manage_topic,
    get_or_404,
    require_unique_slug,
    visible_course_filter,
)

router = APIRouter(tags=["education"])


# --- Education levels ---------------------------------------------------


@router.get("/education-levels", response_model=list[EducationLevelResponse])
def list_education_levels(db: Session = Depends(get_db)) -> list[EducationLevel]:
    return db.query(EducationLevel).order_by(EducationLevel.order_index).all()


@router.post("/education-levels", response_model=EducationLevelResponse, status_code=status.HTTP_201_CREATED)
def create_education_level(
    payload: EducationLevelCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> EducationLevel:
    require_unique_slug(db, EducationLevel, payload.slug)
    level = EducationLevel(**payload.model_dump())
    db.add(level)
    db.commit()
    db.refresh(level)
    return level


# --- Exam boards ----------------------------------------------------------


@router.get("/exam-boards", response_model=list[ExamBoardResponse])
def list_exam_boards(education_level_id: uuid.UUID | None = None, db: Session = Depends(get_db)) -> list[ExamBoard]:
    query = db.query(ExamBoard)
    if education_level_id:
        query = query.filter(ExamBoard.education_level_id == education_level_id)
    return query.order_by(ExamBoard.name).all()


@router.post("/exam-boards", response_model=ExamBoardResponse, status_code=status.HTTP_201_CREATED)
def create_exam_board(
    payload: ExamBoardCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> ExamBoard:
    board = ExamBoard(**payload.model_dump())
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


# --- Subjects ---------------------------------------------------------------


@router.get("/subjects", response_model=list[SubjectResponse])
def list_subjects(
    education_level_id: uuid.UUID | None = None,
    exam_board_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[Subject]:
    query = db.query(Subject)
    if education_level_id:
        query = query.filter(Subject.education_level_id == education_level_id)
    if exam_board_id:
        query = query.filter(Subject.exam_board_id == exam_board_id)
    return query.order_by(Subject.order_index).all()


@router.get("/subjects/{slug}", response_model=SubjectDetail)
def get_subject(
    slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)
) -> SubjectDetail:
    subject = db.query(Subject).filter(Subject.slug == slug).first()
    if not subject:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found.")

    # Build the response without touching subject.courses: assigning a filtered
    # list to that relationship attribute would make SQLAlchemy treat the
    # excluded (unpublished) courses as orphaned and delete them on next flush.
    courses_query = db.query(Course).filter(Course.subject_id == subject.id)
    published_only = visible_course_filter(user)
    if published_only is not None:
        courses_query = courses_query.filter(published_only)
    courses = courses_query.order_by(Course.order_index).all()

    return SubjectDetail(
        **SubjectResponse.model_validate(subject).model_dump(),
        courses=[CourseResponse.model_validate(c) for c in courses],
    )


@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: SubjectCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Subject:
    require_unique_slug(db, Subject, payload.slug)
    get_or_404(db, EducationLevel, payload.education_level_id, "Education level")
    subject = Subject(**payload.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


# --- Courses ------------------------------------------------------------


@router.get("/courses/{slug}", response_model=CourseDetail)
def get_course(
    slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)
) -> Course:
    course = (
        db.query(Course)
        .options(joinedload(Course.chapters).joinedload(Chapter.topics).joinedload(Topic.lessons))
        .filter(Course.slug == slug)
        .first()
    )
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    if not course.is_published and not (user and user.role in (UserRole.ADMIN, UserRole.TEACHER)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")

    course.chapters.sort(key=lambda c: c.order_index)
    for chapter in course.chapters:
        chapter.topics.sort(key=lambda t: t.order_index)
        for topic in chapter.topics:
            topic.lessons.sort(key=lambda l: l.order_index)
    return course


@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate, db: Session = Depends(get_db), user: User = Depends(require_teacher_or_admin)
) -> Course:
    require_unique_slug(db, Course, payload.slug)
    get_or_404(db, Subject, payload.subject_id, "Subject")
    assert_can_manage_subject(db, user, payload.subject_id)
    course = Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.patch("/courses/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: uuid.UUID, payload: CourseUpdate, db: Session = Depends(get_db), user: User = Depends(require_teacher_or_admin)
) -> Course:
    course = assert_can_manage_course(db, user, course_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


# --- Chapters -----------------------------------------------------------


@router.post("/chapters", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
def create_chapter(
    payload: ChapterCreate, db: Session = Depends(get_db), user: User = Depends(require_teacher_or_admin)
) -> Chapter:
    assert_can_manage_course(db, user, payload.course_id)
    chapter = Chapter(**payload.model_dump())
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


# --- Topics ---------------------------------------------------------------


@router.post("/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    payload: TopicCreate, db: Session = Depends(get_db), user: User = Depends(require_teacher_or_admin)
) -> Topic:
    assert_can_manage_chapter(db, user, payload.chapter_id)
    topic = Topic(**payload.model_dump())
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


# --- Lessons ------------------------------------------------------------


@router.post("/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
def create_lesson(
    payload: LessonCreate, db: Session = Depends(get_db), user: User = Depends(require_teacher_or_admin)
) -> Lesson:
    assert_can_manage_topic(db, user, payload.topic_id)
    lesson = Lesson(**payload.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson
