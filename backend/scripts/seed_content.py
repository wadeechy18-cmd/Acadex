"""Seeds sample/demo educational content so the platform isn't empty on first run.

This is placeholder content only, matching the walkthrough example in the product
spec (GCSE -> Edexcel -> Mathematics -> Algebra -> Quadratic Equations -> Solving
Quadratic Equations), plus enough breadth across the other GCSE/A-Level/University
subjects to exercise the browsing UI. It is not production educational content —
replace or remove it once real courses are authored through the teacher/admin
dashboards (Milestones 8-9).

Usage: python -m scripts.seed_content
"""

from app.db.session import SessionLocal
from app.models.content import Note, Video, VideoProvider
from app.models.education import (
    Chapter,
    Course,
    EducationLevel,
    ExamBoard,
    Lesson,
    LessonType,
    Subject,
    Topic,
)


def get_or_create(db, model, defaults: dict | None = None, **filters):
    obj = db.query(model).filter_by(**filters).first()
    if obj:
        return obj, False
    obj = model(**filters, **(defaults or {}))
    db.add(obj)
    db.flush()
    return obj, True


SCIENCE_SUBJECTS = ["Mathematics", "Physics", "Chemistry"]

UNIVERSITY_MODULES = [
    "Programming Fundamentals (Python)",
    "Object-Oriented Programming (Java)",
    "Systems Programming (C/C++)",
    "Data Structures",
    "Algorithms",
    "Computer Architecture",
    "Databases",
    "Operating Systems",
    "Computer Networks",
    "Software Engineering",
    "Discrete Mathematics",
    "Mathematics for Computing",
    "Web Development",
]


def main() -> None:
    db = SessionLocal()
    try:
        gcse, _ = get_or_create(
            db, EducationLevel, slug="gcse", defaults={"name": "GCSE", "order_index": 0}
        )
        a_level, _ = get_or_create(
            db,
            EducationLevel,
            slug="international-a-level",
            defaults={"name": "International A-Level", "order_index": 1},
        )
        university, _ = get_or_create(
            db,
            EducationLevel,
            slug="university-year-1-cs",
            defaults={"name": "University — Year 1 Computer Science", "order_index": 2},
        )

        edexcel_gcse, _ = get_or_create(
            db, ExamBoard, slug="edexcel", education_level_id=gcse.id, defaults={"name": "Pearson Edexcel"}
        )
        oxfordaqa_gcse, _ = get_or_create(
            db, ExamBoard, slug="oxfordaqa", education_level_id=gcse.id, defaults={"name": "OxfordAQA"}
        )
        edexcel_alevel, _ = get_or_create(
            db, ExamBoard, slug="edexcel", education_level_id=a_level.id, defaults={"name": "Pearson Edexcel"}
        )
        cambridge_alevel, _ = get_or_create(
            db, ExamBoard, slug="cambridge", education_level_id=a_level.id, defaults={"name": "Cambridge"}
        )

        for i, subject_name in enumerate(SCIENCE_SUBJECTS):
            get_or_create(
                db,
                Subject,
                slug=f"gcse-edexcel-{subject_name.lower()}",
                defaults={
                    "name": subject_name,
                    "education_level_id": gcse.id,
                    "exam_board_id": edexcel_gcse.id,
                    "order_index": i,
                },
            )
            get_or_create(
                db,
                Subject,
                slug=f"gcse-oxfordaqa-{subject_name.lower()}",
                defaults={
                    "name": subject_name,
                    "education_level_id": gcse.id,
                    "exam_board_id": oxfordaqa_gcse.id,
                    "order_index": i,
                },
            )
            get_or_create(
                db,
                Subject,
                slug=f"alevel-edexcel-{subject_name.lower()}",
                defaults={
                    "name": subject_name,
                    "education_level_id": a_level.id,
                    "exam_board_id": edexcel_alevel.id,
                    "order_index": i,
                },
            )
            get_or_create(
                db,
                Subject,
                slug=f"alevel-cambridge-{subject_name.lower()}",
                defaults={
                    "name": subject_name,
                    "education_level_id": a_level.id,
                    "exam_board_id": cambridge_alevel.id,
                    "order_index": i,
                },
            )

        for i, module_name in enumerate(UNIVERSITY_MODULES):
            slug = "uni-" + module_name.lower().split(" (")[0].replace(" ", "-").replace("/", "")
            get_or_create(
                db,
                Subject,
                slug=slug,
                defaults={"name": module_name, "education_level_id": university.id, "order_index": i},
            )

        db.commit()

        # Fully fleshed example matching the product spec's walkthrough:
        # GCSE -> Edexcel -> Mathematics -> Algebra -> Quadratic Equations
        # -> Solving Quadratic Equations
        maths_subject = db.query(Subject).filter_by(slug="gcse-edexcel-mathematics").first()
        course, _ = get_or_create(
            db,
            Course,
            slug="gcse-edexcel-mathematics-course",
            defaults={
                "subject_id": maths_subject.id,
                "title": "GCSE Mathematics (Edexcel)",
                "description": "The full GCSE Mathematics specification, topic by topic.",
                "is_published": True,
                "order_index": 0,
            },
        )
        algebra, _ = get_or_create(
            db,
            Chapter,
            slug="algebra",
            course_id=course.id,
            defaults={"title": "Algebra", "order_index": 0},
        )
        quadratics, _ = get_or_create(
            db,
            Topic,
            slug="quadratic-equations",
            chapter_id=algebra.id,
            defaults={"title": "Quadratic Equations", "order_index": 0},
        )
        lesson, _ = get_or_create(
            db,
            Lesson,
            slug="solving-quadratic-equations",
            topic_id=quadratics.id,
            defaults={
                "title": "Solving Quadratic Equations",
                "lesson_type": LessonType.MIXED,
                "order_index": 0,
                "is_published": True,
            },
        )

        # Public-domain/Creative-Commons sample video, used only to demonstrate the
        # video player — not a real lesson recording.
        get_or_create(
            db,
            Video,
            lesson_id=lesson.id,
            defaults={
                "provider": VideoProvider.LOCAL,
                "storage_key": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "duration_seconds": 596,
            },
        )

        get_or_create(
            db,
            Note,
            lesson_id=lesson.id,
            title="Solving Quadratic Equations",
            defaults={
                "order_index": 0,
                "content_blocks": [
                    {"type": "heading", "text": "The quadratic formula"},
                    {
                        "type": "paragraph",
                        "text": "Any quadratic equation in the form ax^2 + bx + c = 0 can be solved using the quadratic formula.",
                    },
                    {"type": "formula", "latex": "x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}"},
                    {"type": "key_point", "text": "Always check the discriminant (b^2 - 4ac) first — if it's negative, there are no real roots."},
                    {"type": "example", "text": "Solve x^2 - 5x + 6 = 0: factorises to (x-2)(x-3) = 0, so x = 2 or x = 3."},
                    {"type": "exam_tip", "text": "Show your substitution into the formula for method marks, even if your final answer is wrong."},
                ],
            },
        )

        db.commit()
        print("Seed content created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
