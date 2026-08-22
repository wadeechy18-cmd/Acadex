"""Seeds one fully-worked pilot topic per subject/tier that currently shows an
empty "No courses have been published for this subject yet." placeholder.

This is real, original exam-focused content (not scraped from any textbook or
past paper) written to the same schema/pattern as the Milestone-5 walkthrough
example in seed_content.py: Subject -> Course -> Chapter -> Topic -> Lesson ->
Note.content_blocks, plus practice Questions and a Quiz per topic.

Scope (see docs discussion): one exam board per GCSE/IAL subject (Edexcel),
and University Year 1 consolidated into a single "Computer Science" subject
rather than the 13 flat stub subjects seed_content.py creates. Those stub
subjects (OxfordAQA/Cambridge variants, the 13 old Uni modules) are left
untouched -- this script only adds new rows, it never deletes anything.

Usage: python -m scripts.seed_pilot_content
(Run seed_content.py first, or run standalone -- this script creates any
EducationLevel/ExamBoard/Subject it needs that isn't already there.)
"""

from app.db.session import SessionLocal
from app.models.content import Note
from app.models.education import Chapter, Course, EducationLevel, ExamBoard, Lesson, LessonType, Subject, Topic
from app.models.question import Difficulty, Question, QuestionOption, QuestionType
from app.models.quiz import Quiz, QuizQuestion


def get_or_create(db, model, defaults: dict | None = None, **filters):
    obj = db.query(model).filter_by(**filters).first()
    if obj:
        return obj, False
    obj = model(**filters, **(defaults or {}))
    db.add(obj)
    db.flush()
    return obj, True


def build_topic(db, *, subject, course_title, course_slug, chapter_title, chapter_slug,
                 topic_title, topic_slug, lesson_title, lesson_slug, note_blocks, questions, quiz_title):
    """Creates Course -> Chapter -> Topic -> Lesson -> Note, then the practice
    Questions and a Quiz bundling them, all idempotently. `questions` is a list
    of dicts matching the Question/QuestionOption shape.
    """
    course, _ = get_or_create(
        db, Course, slug=course_slug,
        defaults={"subject_id": subject.id, "title": course_title, "is_published": True, "order_index": 0},
    )
    chapter, _ = get_or_create(
        db, Chapter, slug=chapter_slug, course_id=course.id,
        defaults={"title": chapter_title, "order_index": 0},
    )
    topic, _ = get_or_create(
        db, Topic, slug=topic_slug, chapter_id=chapter.id,
        defaults={"title": topic_title, "order_index": 0},
    )
    lesson, _ = get_or_create(
        db, Lesson, slug=lesson_slug, topic_id=topic.id,
        defaults={"title": lesson_title, "lesson_type": LessonType.NOTES, "order_index": 0, "is_published": True},
    )
    get_or_create(
        db, Note, lesson_id=lesson.id, title=lesson_title,
        defaults={"order_index": 0, "content_blocks": note_blocks},
    )
    db.commit()

    question_rows = []
    for q in questions:
        options = q.pop("options", None)
        question, created = get_or_create(
            db, Question, prompt=q.pop("prompt"), subject_id=subject.id,
            defaults={"topic_id": topic.id, "chapter_id": chapter.id, "is_published": True, **q},
        )
        if created and options:
            db.add_all(
                QuestionOption(question_id=question.id, text=o["text"], is_correct=o["is_correct"], order_index=i)
                for i, o in enumerate(options)
            )
        db.commit()
        question_rows.append(question)

    quiz, created = get_or_create(
        db, Quiz, title=quiz_title, topic_id=topic.id, defaults={"has_timer": False, "is_published": True}
    )
    if created:
        db.add_all(
            QuizQuestion(quiz_id=quiz.id, question_id=question.id, order_index=i)
            for i, question in enumerate(question_rows)
        )
        db.commit()

    return topic


def main() -> None:
    db = SessionLocal()
    try:
        gcse, _ = get_or_create(db, EducationLevel, slug="gcse", defaults={"name": "GCSE", "order_index": 0})
        a_level, _ = get_or_create(
            db, EducationLevel, slug="international-a-level",
            defaults={"name": "International A-Level", "order_index": 1},
        )
        university, _ = get_or_create(
            db, EducationLevel, slug="university-year-1-cs",
            defaults={"name": "University — Year 1 Computer Science", "order_index": 2},
        )

        edexcel_gcse, _ = get_or_create(
            db, ExamBoard, slug="edexcel", education_level_id=gcse.id, defaults={"name": "Pearson Edexcel"}
        )
        edexcel_alevel, _ = get_or_create(
            db, ExamBoard, slug="edexcel", education_level_id=a_level.id, defaults={"name": "Pearson Edexcel"}
        )

        def subject(slug, name, level, exam_board=None, order_index=0):
            obj, _ = get_or_create(
                db, Subject, slug=slug,
                defaults={
                    "name": name, "education_level_id": level.id,
                    "exam_board_id": exam_board.id if exam_board else None, "order_index": order_index,
                },
            )
            return obj

        gcse_physics = subject("gcse-edexcel-physics", "Physics", gcse, edexcel_gcse, 1)
        gcse_chemistry = subject("gcse-edexcel-chemistry", "Chemistry", gcse, edexcel_gcse, 2)
        gcse_cs = subject("gcse-edexcel-computer-science", "Computer Science", gcse, edexcel_gcse, 3)
        ial_maths = subject("alevel-edexcel-mathematics", "Mathematics", a_level, edexcel_alevel, 0)
        ial_physics = subject("alevel-edexcel-physics", "Physics", a_level, edexcel_alevel, 1)
        ial_chemistry = subject("alevel-edexcel-chemistry", "Chemistry", a_level, edexcel_alevel, 2)
        ial_cs = subject("alevel-edexcel-computer-science", "Computer Science", a_level, edexcel_alevel, 3)
        uni_cs = subject("university-computer-science", "Computer Science", university, None, 0)
        db.commit()

        # ---- GCSE Physics: Energy ----------------------------------------
        build_topic(
            db, subject=gcse_physics,
            course_title="GCSE Physics (Edexcel)", course_slug="gcse-edexcel-physics-course",
            chapter_title="Energy", chapter_slug="energy",
            topic_title="Energy Stores and Transfers", topic_slug="energy-stores-and-transfers",
            lesson_title="Energy Stores, Transfers and Efficiency", lesson_slug="energy-stores-transfers-and-efficiency",
            note_blocks=[
                {"type": "heading", "text": "Energy stores"},
                {"type": "paragraph", "text": "Energy is never created or destroyed — it is transferred between eight stores: kinetic, gravitational potential, elastic potential, thermal (internal), chemical, magnetic, electrostatic, and nuclear. A 'change' in a system means energy has moved from one store to another."},
                {"type": "formula", "latex": "E_k = \\tfrac{1}{2}mv^2"},
                {"type": "formula", "latex": "E_p = mgh"},
                {"type": "example", "text": "A 2 kg ball moving at 3 m/s has kinetic energy E_k = 0.5 x 2 x 3^2 = 9 J."},
                {"type": "heading", "text": "Conservation of energy and efficiency"},
                {"type": "paragraph", "text": "The total energy transferred to a system always equals the total transferred away from it — energy is conserved. In practice, useful transfers are always accompanied by 'wasted' transfers, usually to the thermal store of the surroundings via friction or resistance."},
                {"type": "formula", "latex": "\\text{efficiency} = \\frac{\\text{useful output energy transfer}}{\\text{total input energy transfer}} \\times 100\\%"},
                {"type": "key_point", "text": "No device can be 100% efficient, because some energy is always dissipated (usually as heat) to the surroundings rather than to the useful store."},
                {"type": "exam_tip", "text": "Common mistake: writing 'energy is lost'. Energy is never lost — it is dissipated/transferred to a less useful store (usually thermal energy of the surroundings). Examiners specifically penalise 'lost' with no elaboration."},
                {"type": "exam_tip", "text": "Top grade tip: for 6-mark efficiency/energy questions, always state the conservation law explicitly before doing the calculation — it's often a method mark on its own."},
            ],
            questions=[
                {
                    "prompt": "A 2 kg object is moving at 4 m/s. Calculate its kinetic energy in joules.",
                    "question_type": QuestionType.NUMERICAL, "difficulty": Difficulty.EASY, "marks": 2,
                    "correct_answer": "16",
                    "explanation": "E_k = 0.5 x m x v^2 = 0.5 x 2 x 4^2 = 0.5 x 2 x 16 = 16 J.",
                },
                {
                    "prompt": "A motor transfers 500 J of electrical energy and produces 350 J of useful kinetic energy. What is its efficiency?",
                    "question_type": QuestionType.MCQ, "difficulty": Difficulty.MEDIUM, "marks": 2,
                    "explanation": "efficiency = useful output / total input x 100 = 350/500 x 100 = 70%.",
                    "options": [
                        {"text": "70%", "is_correct": True},
                        {"text": "35%", "is_correct": False},
                        {"text": "50%", "is_correct": False},
                        {"text": "150%", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Explain why a real machine can never be 100% efficient. (3 marks)",
                    "question_type": QuestionType.STRUCTURED, "difficulty": Difficulty.MEDIUM, "marks": 3,
                    "explanation": "Model answer: In any real process, some energy is always transferred to non-useful stores (1 mark) — usually the thermal store of the surroundings, via friction, air resistance, or electrical resistance (1 mark). Because total energy is conserved but not all of it reaches the useful store, useful output energy is always less than total input energy, so efficiency is always below 100% (1 mark). Common mistake: saying energy 'disappears' or is 'used up' — energy is always conserved, just transferred somewhere less useful.",
                },
            ],
            quiz_title="Energy Stores and Transfers Quiz",
        )

        # ---- GCSE Chemistry: Atomic Structure ----------------------------
        build_topic(
            db, subject=gcse_chemistry,
            course_title="GCSE Chemistry (Edexcel)", course_slug="gcse-edexcel-chemistry-course",
            chapter_title="Atomic Structure and the Periodic Table", chapter_slug="atomic-structure-and-periodic-table",
            topic_title="Atomic Structure", topic_slug="atomic-structure",
            lesson_title="Structure of the Atom", lesson_slug="structure-of-the-atom",
            note_blocks=[
                {"type": "heading", "text": "Subatomic particles"},
                {"type": "paragraph", "text": "An atom has a small, dense, positively charged nucleus (containing protons and neutrons) surrounded by electrons in shells. Protons have a relative charge of +1 and relative mass 1; neutrons have no charge and relative mass 1; electrons have a relative charge of -1 and negligible mass."},
                {"type": "key_point", "text": "Atomic number = number of protons (defines the element). Mass number = protons + neutrons. In a neutral atom, number of electrons = number of protons."},
                {"type": "example", "text": "Sodium has atomic number 11 and mass number 23. It has 11 protons, 11 electrons, and 23 - 11 = 12 neutrons."},
                {"type": "heading", "text": "Isotopes and electronic structure"},
                {"type": "paragraph", "text": "Isotopes are atoms of the same element (same number of protons) with different numbers of neutrons, and therefore different mass numbers. Electrons occupy shells around the nucleus, filling the lowest-energy shell first: 2, then 8, then 8."},
                {"type": "example", "text": "Chlorine (atomic number 17) has electronic structure 2,8,7 — 2 in the first shell, 8 in the second, 7 in the third (outer) shell."},
                {"type": "exam_tip", "text": "Common mistake: confusing atomic number and mass number, or forgetting that isotopes have identical chemical properties because they have the same number of electrons — only the physical property of mass differs."},
                {"type": "exam_tip", "text": "Top grade tip: when asked to 'deduce' an electronic structure, always show the shell-filling working (2, 8, 8...) rather than just stating the final answer — method marks are available."},
            ],
            questions=[
                {
                    "prompt": "An atom of aluminium has atomic number 13 and mass number 27. How many neutrons does it have?",
                    "question_type": QuestionType.NUMERICAL, "difficulty": Difficulty.EASY, "marks": 1,
                    "correct_answer": "14",
                    "explanation": "Neutrons = mass number - atomic number = 27 - 13 = 14.",
                },
                {
                    "prompt": "Which statement correctly describes an isotope?",
                    "question_type": QuestionType.MCQ, "difficulty": Difficulty.MEDIUM, "marks": 1,
                    "explanation": "Isotopes have the same number of protons (same atomic number) but a different number of neutrons, giving a different mass number.",
                    "options": [
                        {"text": "Same number of protons, different number of neutrons", "is_correct": True},
                        {"text": "Same number of neutrons, different number of protons", "is_correct": False},
                        {"text": "Same mass number, different atomic number", "is_correct": False},
                        {"text": "Different element, same physical properties", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Explain why isotopes of the same element have identical chemical properties. (2 marks)",
                    "question_type": QuestionType.STRUCTURED, "difficulty": Difficulty.MEDIUM, "marks": 2,
                    "explanation": "Model answer: Chemical properties depend on the number and arrangement of electrons, especially in the outer shell (1 mark). Isotopes of the same element have the same number of protons and therefore the same number of electrons in a neutral atom, so their electronic structure — and hence chemical behaviour — is identical, even though their mass differs (1 mark).",
                },
            ],
            quiz_title="Atomic Structure Quiz",
        )

        # ---- GCSE Computer Science: Algorithms ----------------------------
        build_topic(
            db, subject=gcse_cs,
            course_title="GCSE Computer Science (Edexcel)", course_slug="gcse-edexcel-computer-science-course",
            chapter_title="Algorithms", chapter_slug="algorithms",
            topic_title="Searching and Sorting Algorithms", topic_slug="searching-and-sorting-algorithms",
            lesson_title="Searching and Sorting Algorithms", lesson_slug="searching-and-sorting-algorithms",
            note_blocks=[
                {"type": "heading", "text": "Linear search vs binary search"},
                {"type": "paragraph", "text": "Linear search checks every item in a list, one at a time, from the start, until it finds the target or reaches the end. It works on any list (sorted or not) but is slow for large lists."},
                {"type": "paragraph", "text": "Binary search only works on a SORTED list. It repeatedly checks the middle item: if the target is smaller, it discards the upper half; if larger, it discards the lower half; it repeats until found."},
                {"type": "example", "text": "Searching for 7 in [1,3,5,7,9,11,13] by binary search: middle is 7 (index 3) — found immediately in 1 comparison, versus up to 4 comparisons for linear search."},
                {"type": "key_point", "text": "Binary search is much faster than linear search for large lists, but only works if the list is already sorted — sorting it first has its own cost."},
                {"type": "heading", "text": "Bubble sort"},
                {"type": "paragraph", "text": "Bubble sort repeatedly compares adjacent pairs of items and swaps them if they are in the wrong order, making multiple passes through the list until no swaps are needed."},
                {"type": "example", "text": "Sorting [5,2,4]: pass 1 compares (5,2) -> swap -> [2,5,4]; compares (5,4) -> swap -> [2,4,5]. Pass 2 makes no swaps, so the list [2,4,5] is sorted."},
                {"type": "exam_tip", "text": "Common mistake: describing binary search as working on any list. Always state the precondition that the list must be sorted first — this is a frequently missed mark."},
                {"type": "exam_tip", "text": "Top grade tip: for 'compare' questions, structure your answer around one clear point of similarity/difference at a time (e.g. speed, precondition, implementation complexity) rather than describing each algorithm separately."},
            ],
            questions=[
                {
                    "prompt": "Which precondition must be true for binary search to work correctly?",
                    "question_type": QuestionType.MCQ, "difficulty": Difficulty.EASY, "marks": 1,
                    "explanation": "Binary search repeatedly halves the search space by comparing to the middle value, which only gives a correct result if the list is already sorted.",
                    "options": [
                        {"text": "The list must be sorted", "is_correct": True},
                        {"text": "The list must contain only numbers", "is_correct": False},
                        {"text": "The list must have an even number of items", "is_correct": False},
                        {"text": "The list must be reversed first", "is_correct": False},
                    ],
                },
                {
                    "prompt": "A sorted list has 15 items. What is the maximum number of comparisons binary search needs in the worst case?",
                    "question_type": QuestionType.NUMERICAL, "difficulty": Difficulty.MEDIUM, "marks": 2,
                    "correct_answer": "4",
                    "explanation": "Binary search halves the list each comparison: 15 -> 7 -> 3 -> 1 -> 0, which is ceil(log2(15+1)) = 4 comparisons in the worst case.",
                },
                {
                    "prompt": "Compare linear search and binary search in terms of speed and the conditions needed to use them. (4 marks)",
                    "question_type": QuestionType.STRUCTURED, "difficulty": Difficulty.HARD, "marks": 4,
                    "explanation": "Model answer: Linear search checks items one at a time from the start and works on any list, sorted or not (1 mark), but in the worst case takes n comparisons for a list of n items, making it slow for large lists (1 mark). Binary search repeatedly halves the search space (1 mark), giving it far fewer comparisons (log2 n) for large lists, but it only works correctly if the list is already sorted, which adds a setup cost if it isn't (1 mark).",
                },
            ],
            quiz_title="Searching and Sorting Algorithms Quiz",
        )

        # ---- IAL Mathematics: Differentiation (Pure Maths) ----------------
        build_topic(
            db, subject=ial_maths,
            course_title="International A-Level Mathematics (Edexcel)", course_slug="ial-edexcel-mathematics-course",
            chapter_title="Pure Mathematics", chapter_slug="pure-mathematics",
            topic_title="Differentiation", topic_slug="differentiation",
            lesson_title="Introduction to Differentiation", lesson_slug="introduction-to-differentiation",
            note_blocks=[
                {"type": "heading", "text": "The gradient function"},
                {"type": "paragraph", "text": "Differentiation finds the gradient of a curve at any point, by finding the gradient of the tangent to the curve. The derivative of y with respect to x is written dy/dx, or f'(x) for y = f(x)."},
                {"type": "formula", "latex": "\\frac{d}{dx}(x^n) = nx^{n-1}"},
                {"type": "paragraph", "text": "This power rule applies term by term to any polynomial. Constants differentiate to zero, since they have no gradient."},
                {"type": "example", "text": "If y = 3x^4 - 5x^2 + 7, then dy/dx = 12x^3 - 10x."},
                {"type": "heading", "text": "Stationary points"},
                {"type": "paragraph", "text": "A stationary point occurs where dy/dx = 0. The second derivative, d^2y/dx^2, tells you its nature: positive means a minimum, negative means a maximum, and zero requires further checking (it may be a point of inflection)."},
                {"type": "example", "text": "For y = x^3 - 3x, dy/dx = 3x^2 - 3 = 0 gives x = 1 or x = -1. d^2y/dx^2 = 6x, so at x = 1 (positive) it's a minimum, and at x = -1 (negative) it's a maximum."},
                {"type": "exam_tip", "text": "Common mistake: forgetting to justify the nature of a stationary point with the second derivative test (or a sign check either side) — 'dy/dx = 0' alone only proves it's stationary, not what type."},
                {"type": "exam_tip", "text": "Top grade tip: always rewrite roots and fractions as powers of x (e.g. sqrt(x) = x^{1/2}, 1/x^2 = x^{-2}) before differentiating with the power rule."},
            ],
            questions=[
                {
                    "prompt": "Find dy/dx for y = 4x^3 - 2x, then evaluate it at x = 2. Give a single number.",
                    "question_type": QuestionType.NUMERICAL, "difficulty": Difficulty.MEDIUM, "marks": 3,
                    "correct_answer": "46",
                    "explanation": "dy/dx = 12x^2 - 2. At x = 2: 12(4) - 2 = 48 - 2 = 46.",
                },
                {
                    "prompt": "What is d/dx(x^5)?",
                    "question_type": QuestionType.MCQ, "difficulty": Difficulty.EASY, "marks": 1,
                    "explanation": "By the power rule, d/dx(x^n) = n x^(n-1), so d/dx(x^5) = 5x^4.",
                    "options": [
                        {"text": "5x^4", "is_correct": True},
                        {"text": "x^4", "is_correct": False},
                        {"text": "5x^5", "is_correct": False},
                        {"text": "4x^5", "is_correct": False},
                    ],
                },
                {
                    "prompt": "For y = x^3 - 3x, justify whether the stationary point at x = -1 is a maximum or a minimum. (3 marks)",
                    "question_type": QuestionType.STRUCTURED, "difficulty": Difficulty.HARD, "marks": 3,
                    "explanation": "Model answer: dy/dx = 3x^2 - 3, and d^2y/dx^2 = 6x (1 mark). At x = -1, d^2y/dx^2 = 6(-1) = -6, which is negative (1 mark). Since the second derivative is negative, the stationary point at x = -1 is a maximum (1 mark). Common mistake: stating the point is stationary without checking its nature, or misapplying the sign convention (negative = maximum, positive = minimum).",
                },
            ],
            quiz_title="Differentiation Quiz",
        )

        # ---- IAL Physics: Kinematics (Mechanics) --------------------------
        build_topic(
            db, subject=ial_physics,
            course_title="International A-Level Physics (Edexcel)", course_slug="ial-edexcel-physics-course",
            chapter_title="Mechanics", chapter_slug="mechanics",
            topic_title="Kinematics", topic_slug="kinematics",
            lesson_title="SUVAT Equations and Motion Graphs", lesson_slug="suvat-equations-and-motion-graphs",
            note_blocks=[
                {"type": "heading", "text": "The SUVAT equations"},
                {"type": "paragraph", "text": "For motion in a straight line with constant acceleration, five quantities are related: s (displacement), u (initial velocity), v (final velocity), a (acceleration), t (time)."},
                {"type": "formula", "latex": "v = u + at"},
                {"type": "formula", "latex": "s = ut + \\tfrac{1}{2}at^2"},
                {"type": "formula", "latex": "v^2 = u^2 + 2as"},
                {"type": "formula", "latex": "s = \\tfrac{(u+v)}{2}t"},
                {"type": "example", "text": "A car starts at rest (u = 0) and accelerates at 3 m/s^2 for 5 s. v = u + at = 0 + 3(5) = 15 m/s. Displacement s = ut + 0.5at^2 = 0 + 0.5(3)(25) = 37.5 m."},
                {"type": "heading", "text": "Motion graphs"},
                {"type": "paragraph", "text": "On a velocity-time graph, the gradient equals acceleration, and the area under the graph equals displacement. On a displacement-time graph, the gradient equals velocity."},
                {"type": "key_point", "text": "The SUVAT equations only apply when acceleration is constant — they cannot be used directly if acceleration is changing."},
                {"type": "exam_tip", "text": "Common mistake: applying SUVAT equations to a situation with non-constant acceleration (e.g. with air resistance included), or mixing up which quantity is missing before selecting the equation."},
                {"type": "exam_tip", "text": "Top grade tip: list the five SUVAT quantities and label which three are known and which is asked for before picking an equation — it makes selecting the right one far quicker under exam pressure."},
            ],
            questions=[
                {
                    "prompt": "A ball starts at rest and accelerates uniformly at 4 m/s^2 for 6 s. What is its final velocity in m/s?",
                    "question_type": QuestionType.NUMERICAL, "difficulty": Difficulty.EASY, "marks": 2,
                    "correct_answer": "24",
                    "explanation": "v = u + at = 0 + 4(6) = 24 m/s.",
                },
                {
                    "prompt": "On a velocity-time graph, what does the area under the graph represent?",
                    "question_type": QuestionType.MCQ, "difficulty": Difficulty.EASY, "marks": 1,
                    "explanation": "The area under a velocity-time graph equals the displacement, since displacement is the integral of velocity with respect to time.",
                    "options": [
                        {"text": "Displacement", "is_correct": True},
                        {"text": "Acceleration", "is_correct": False},
                        {"text": "Average speed", "is_correct": False},
                        {"text": "Force", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Evaluate the assumptions made when using the SUVAT equations to model the motion of a falling object in real life. (3 marks)",
                    "question_type": QuestionType.STRUCTURED, "difficulty": Difficulty.HARD, "marks": 3,
                    "explanation": "Model answer: SUVAT equations assume constant acceleration, so they assume air resistance is negligible and gravitational field strength is constant over the fall (1 mark). In reality, air resistance increases with speed, causing acceleration to decrease as the object speeds up, particularly for light or large-surface-area objects, so the model becomes less accurate over long falls or high speeds (1 mark). For short falls of dense objects, air resistance is small enough that the constant-acceleration assumption remains a reasonable approximation (1 mark).",
                },
            ],
            quiz_title="Kinematics Quiz",
        )

        # ---- IAL Chemistry: Electron Configuration -------------------------
        build_topic(
            db, subject=ial_chemistry,
            course_title="International A-Level Chemistry (Edexcel)", course_slug="ial-edexcel-chemistry-course",
            chapter_title="Atomic Structure and Bonding", chapter_slug="atomic-structure-and-bonding",
            topic_title="Electron Configuration", topic_slug="electron-configuration",
            lesson_title="Electron Configuration and Orbitals", lesson_slug="electron-configuration-and-orbitals",
            note_blocks=[
                {"type": "heading", "text": "Orbitals and sub-shells"},
                {"type": "paragraph", "text": "Electrons occupy orbitals grouped into s, p, d and f sub-shells. An s sub-shell holds up to 2 electrons, p holds up to 6, and d holds up to 10. Sub-shells fill in order of increasing energy (the Aufbau principle), which is not always the same as increasing shell number — 4s fills before 3d."},
                {"type": "formula", "latex": "1s^2\\,2s^2\\,2p^6\\,3s^2\\,3p^6\\,4s^2\\,3d^{10}\\,4p^6"},
                {"type": "example", "text": "Iron (atomic number 26) has electron configuration 1s2 2s2 2p6 3s2 3p6 4s2 3d6. Note that 4s fills before 3d, following the Aufbau order, even though 3d is 'shell 3'."},
                {"type": "heading", "text": "Ionisation energy trends"},
                {"type": "paragraph", "text": "First ionisation energy generally increases across a period, because nuclear charge increases while shielding stays roughly constant, pulling the outer electron in more strongly. It decreases down a group, because extra electron shells increase the distance from the nucleus and add shielding, outweighing the increased nuclear charge."},
                {"type": "key_point", "text": "Small dips in the general increasing trend across a period occur at group 3 (starting to fill a p sub-shell, which is higher energy than a full s sub-shell) and group 6 (a p sub-shell electron is paired, causing repulsion that makes it easier to remove)."},
                {"type": "exam_tip", "text": "Common mistake: writing '4s2 3d10' in the wrong energy order when listing configurations, or forgetting the anomalous dips (at groups 3 and 6) when asked to explain a periodic trend in full."},
                {"type": "exam_tip", "text": "Top grade tip: when explaining ionisation energy, always name all three factors — nuclear charge, shielding, and atomic radius/distance — even if only one is dominant, since 'explain' questions award marks for each correctly linked factor."},
            ],
            questions=[
                {
                    "prompt": "What is the full electron configuration of a sodium atom (atomic number 11)?",
                    "question_type": QuestionType.SHORT_ANSWER, "difficulty": Difficulty.MEDIUM, "marks": 1,
                    "correct_answer": "1s2 2s2 2p6 3s1",
                    "explanation": "Sodium has 11 electrons, filling 1s (2), 2s (2), 2p (6), then 1 electron into 3s: 1s2 2s2 2p6 3s1.",
                },
                {
                    "prompt": "Which sub-shell fills before the 3d sub-shell, according to the Aufbau principle?",
                    "question_type": QuestionType.MCQ, "difficulty": Difficulty.MEDIUM, "marks": 1,
                    "explanation": "The 4s sub-shell is lower in energy than 3d and fills first, even though 3d belongs to a lower shell number.",
                    "options": [
                        {"text": "4s", "is_correct": True},
                        {"text": "4p", "is_correct": False},
                        {"text": "3p", "is_correct": False},
                        {"text": "4d", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Explain why first ionisation energy generally increases across period 3 (Na to Ar). (3 marks)",
                    "question_type": QuestionType.STRUCTURED, "difficulty": Difficulty.HARD, "marks": 3,
                    "explanation": "Model answer: Across the period, nuclear charge increases as protons are added (1 mark), while the outer electrons are added to the same shell, so shielding stays roughly constant and atomic radius decreases (1 mark). The stronger nuclear attraction on the outer electrons, over a similar distance, means more energy is needed to remove one, so first ionisation energy increases overall (1 mark). Common mistake: not mentioning shielding staying constant, which is the key reason nuclear charge dominates the trend.",
                },
            ],
            quiz_title="Electron Configuration Quiz",
        )

        # ---- IAL Computer Science: OOP Fundamentals ------------------------
        build_topic(
            db, subject=ial_cs,
            course_title="International A-Level Computer Science (Edexcel)", course_slug="ial-edexcel-computer-science-course",
            chapter_title="Object-Oriented Programming", chapter_slug="object-oriented-programming",
            topic_title="OOP Fundamentals", topic_slug="oop-fundamentals",
            lesson_title="Classes, Objects and Encapsulation", lesson_slug="classes-objects-and-encapsulation",
            note_blocks=[
                {"type": "heading", "text": "Classes and objects"},
                {"type": "paragraph", "text": "A class is a blueprint that defines the attributes (data) and methods (behaviour) an object will have. An object is a specific instance of a class, created (instantiated) from it, with its own copy of the attribute values."},
                {"type": "example", "text": "class Car:\n    def __init__(self, make, speed):\n        self.make = make\n        self.speed = speed\n    def accelerate(self, amount):\n        self.speed += amount\n\nmy_car = Car(\"Toyota\", 0)\nmy_car.accelerate(20)\nprint(my_car.speed)  # 20"},
                {"type": "paragraph", "text": "Here, Car is the class; my_car is an object (instance) of that class, with its own make and speed attributes independent of any other Car object."},
                {"type": "heading", "text": "Encapsulation"},
                {"type": "paragraph", "text": "Encapsulation means bundling an object's data with the methods that operate on it, and restricting direct access to that data from outside the class (often via private attributes and public 'getter'/'setter' methods). This protects the object's internal state from being changed in invalid ways."},
                {"type": "key_point", "text": "Encapsulation is one of the four pillars of OOP, alongside inheritance, polymorphism, and abstraction. It improves maintainability by hiding implementation detail behind a stable interface."},
                {"type": "exam_tip", "text": "Common mistake: confusing a class with an object in a written answer — always be precise about which one you mean, since 'the class stores 20' vs 'the object stores 20' are not interchangeable."},
                {"type": "exam_tip", "text": "Top grade tip: when tracing code involving objects, draw out each object's attribute values as they change line by line — this avoids the most common code-tracing error of using stale values."},
            ],
            questions=[
                {
                    "prompt": "In the class definition above, what value is stored in my_car.speed immediately after it is created (before accelerate is called)?",
                    "question_type": QuestionType.NUMERICAL, "difficulty": Difficulty.EASY, "marks": 1,
                    "correct_answer": "0",
                    "explanation": "Car(\"Toyota\", 0) passes speed=0 into __init__, which sets self.speed = 0.",
                },
                {
                    "prompt": "Which of the following best describes the relationship between a class and an object?",
                    "question_type": QuestionType.MCQ, "difficulty": Difficulty.EASY, "marks": 1,
                    "explanation": "A class is a blueprint/template; an object is a specific instance created from that blueprint, with its own attribute values.",
                    "options": [
                        {"text": "A class is a blueprint; an object is an instance of it", "is_correct": True},
                        {"text": "An object is a blueprint; a class is an instance of it", "is_correct": False},
                        {"text": "They are always the same thing", "is_correct": False},
                        {"text": "A class can only ever have one object", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Compare object-oriented programming with procedural programming in terms of how data and behaviour are organised. (4 marks)",
                    "question_type": QuestionType.STRUCTURED, "difficulty": Difficulty.HARD, "marks": 4,
                    "explanation": "Model answer: In procedural programming, data and the functions that act on it are kept separate, with data typically passed between independent functions (1 mark), which can make it harder to control which parts of a program can modify shared data (1 mark). In object-oriented programming, data and the methods that operate on it are bundled together inside objects (1 mark), and encapsulation can restrict direct access to that data, making large programs easier to maintain and reason about as they grow (1 mark).",
                },
            ],
            quiz_title="OOP Fundamentals Quiz",
        )

        # ---- University Year 1 CS: Discrete Mathematics --------------------
        build_topic(
            db, subject=uni_cs,
            course_title="Computer Science — Year 1", course_slug="university-computer-science-course",
            chapter_title="Discrete Mathematics", chapter_slug="discrete-mathematics",
            topic_title="Sets, Logic and Proof", topic_slug="sets-logic-and-proof",
            lesson_title="Introduction to Discrete Mathematics", lesson_slug="introduction-to-discrete-mathematics",
            note_blocks=[
                {"type": "heading", "text": "Sets"},
                {"type": "paragraph", "text": "A set is an unordered collection of distinct elements, written e.g. A = {1, 2, 3}. Key operations: union (A ∪ B, elements in A or B), intersection (A ∩ B, elements in both), and difference (A \\ B, elements in A but not B)."},
                {"type": "formula", "latex": "A = \\{1,2,3\\},\\ B = \\{2,3,4\\} \\Rightarrow A \\cup B = \\{1,2,3,4\\},\\ A \\cap B = \\{2,3\\}"},
                {"type": "heading", "text": "Propositional logic"},
                {"type": "paragraph", "text": "Propositional logic combines true/false statements with connectives: AND (∧), OR (∨), NOT (¬), and implication (→). A truth table lists every combination of input truth values and the resulting output."},
                {"type": "example", "text": "For p → q ('if p then q'), the only case where the statement is FALSE is when p is TRUE and q is FALSE — every other combination (including p FALSE) makes the implication TRUE."},
                {"type": "heading", "text": "Proof by induction"},
                {"type": "paragraph", "text": "Mathematical induction proves a statement P(n) holds for all natural numbers n >= some base case, in two steps: (1) Base case — show P(base) is true. (2) Inductive step — assume P(k) is true for some k (the inductive hypothesis), then show this implies P(k+1) is true."},
                {"type": "example", "text": "Prove 1+2+...+n = n(n+1)/2 by induction. Base case n=1: LHS=1, RHS=1(2)/2=1, true. Inductive step: assume 1+...+k = k(k+1)/2. Then 1+...+k+(k+1) = k(k+1)/2 + (k+1) = (k+1)(k/2 + 1) = (k+1)(k+2)/2, which is the formula for n=k+1. So it holds for all n by induction."},
                {"type": "key_point", "text": "A proof by induction is incomplete without BOTH the base case and the inductive step stated explicitly — a common mark loss in problem sheets is skipping the base case as 'obvious'."},
                {"type": "exam_tip", "text": "Common mistake: in the inductive step, assuming what you're trying to prove for n=k+1 directly, rather than deriving it from the inductive hypothesis for n=k. Always start from the k-case and build up to k+1."},
            ],
            questions=[
                {
                    "prompt": "Let A = {1,2,3,4} and B = {3,4,5,6}. How many elements are in A ∩ B?",
                    "question_type": QuestionType.NUMERICAL, "difficulty": Difficulty.EASY, "marks": 1,
                    "correct_answer": "2",
                    "explanation": "A ∩ B = {3,4}, which has 2 elements.",
                },
                {
                    "prompt": "For the implication p → q, in which single case is the statement FALSE?",
                    "question_type": QuestionType.MCQ, "difficulty": Difficulty.MEDIUM, "marks": 1,
                    "explanation": "p → q is only false when p is true and q is false; it is true in every other combination, including when p is false.",
                    "options": [
                        {"text": "p is TRUE and q is FALSE", "is_correct": True},
                        {"text": "p is FALSE and q is TRUE", "is_correct": False},
                        {"text": "p is FALSE and q is FALSE", "is_correct": False},
                        {"text": "p is TRUE and q is TRUE", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Prove by induction that 1 + 2 + ... + n = n(n+1)/2 for all n >= 1. Show the base case and the full inductive step.",
                    "question_type": QuestionType.STRUCTURED, "difficulty": Difficulty.HARD, "marks": 5,
                    "explanation": "Model answer: Base case (n=1): LHS = 1, RHS = 1(2)/2 = 1, so the statement holds. Inductive hypothesis: assume 1+2+...+k = k(k+1)/2 holds for some k >= 1. Inductive step: 1+2+...+k+(k+1) = k(k+1)/2 + (k+1) [by the hypothesis] = (k+1)(k/2 + 1) = (k+1)(k+2)/2, which is exactly the formula for n = k+1. Since the base case holds and the inductive step shows truth for k implies truth for k+1, by the principle of mathematical induction the formula holds for all n >= 1. Common mistake: omitting the base case, or not explicitly substituting the inductive hypothesis into the k+1 expression.",
                },
            ],
            quiz_title="Sets, Logic and Proof Quiz",
        )

        print("Pilot content created: GCSE Physics/Chemistry/Computer Science, "
              "IAL Mathematics/Physics/Chemistry/Computer Science, University Computer Science.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
