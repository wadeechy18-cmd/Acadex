from app.models.question import Difficulty, Question, QuestionOption, QuestionType
from app.models.quiz import Quiz, QuizQuestion
from tests.conftest import auth_headers, register


def _mcq_with_quiz(db_session, subject, topic):
    question = Question(
        subject_id=subject.id,
        topic_id=topic.id,
        question_type=QuestionType.MCQ,
        difficulty=Difficulty.MEDIUM,
        marks=2,
        prompt="2 + 2 = ?",
        explanation="Basic addition.",
        is_published=True,
    )
    db_session.add(question)
    db_session.flush()
    correct = QuestionOption(question_id=question.id, text="4", is_correct=True, order_index=0)
    wrong = QuestionOption(question_id=question.id, text="5", is_correct=False, order_index=1)
    db_session.add_all([correct, wrong])

    numerical = Question(
        subject_id=subject.id,
        topic_id=topic.id,
        question_type=QuestionType.NUMERICAL,
        difficulty=Difficulty.EASY,
        marks=1,
        prompt="10 / 2 = ?",
        correct_answer="5",
        is_published=True,
    )
    db_session.add(numerical)
    db_session.flush()

    quiz = Quiz(topic_id=topic.id, title="Quiz", is_published=True)
    db_session.add(quiz)
    db_session.flush()
    db_session.add_all(
        [
            QuizQuestion(quiz_id=quiz.id, question_id=question.id, order_index=0),
            QuizQuestion(quiz_id=quiz.id, question_id=numerical.id, order_index=1),
        ]
    )
    db_session.commit()
    return quiz, question, correct, wrong, numerical


def test_check_answer_mcq_correct_and_incorrect(client, db_session, published_course):
    topic = published_course.chapters[0].topics[0]
    _, question, correct, wrong, _ = _mcq_with_quiz(db_session, published_course.subject, topic)

    right = client.post(f"/api/v1/questions/{question.id}/check", json={"answer": str(correct.id)})
    assert right.json()["is_correct"] is True

    incorrect = client.post(f"/api/v1/questions/{question.id}/check", json={"answer": str(wrong.id)})
    assert incorrect.json()["is_correct"] is False
    assert incorrect.json()["correct_answer"] == "4"


def test_check_answer_numerical_tolerates_decimal_form(client, db_session, published_course):
    topic = published_course.chapters[0].topics[0]
    _, _, _, _, numerical = _mcq_with_quiz(db_session, published_course.subject, topic)

    res = client.post(f"/api/v1/questions/{numerical.id}/check", json={"answer": "5.0"})
    assert res.json()["is_correct"] is True


def test_quiz_full_attempt_scoring(client, db_session, published_course):
    topic = published_course.chapters[0].topics[0]
    quiz, question, correct, _wrong, numerical = _mcq_with_quiz(db_session, published_course.subject, topic)

    student = register(client, "student")
    attempt = client.post(f"/api/v1/quizzes/{quiz.id}/attempts", headers=auth_headers(student))
    assert attempt.status_code == 201
    attempt_id = attempt.json()["id"]

    submit = client.post(
        f"/api/v1/quiz-attempts/{attempt_id}/submit",
        json={"answers": [{"question_id": str(question.id), "answer": str(correct.id)}, {"question_id": str(numerical.id), "answer": "999"}]},
        headers=auth_headers(student),
    )
    assert submit.status_code == 200
    body = submit.json()
    assert body["score"] == 2  # only the 2-mark MCQ was correct, out of 3 total
    assert body["percentage"] == round(2 / 3 * 100, 1)


def test_quiz_cannot_be_submitted_twice(client, db_session, published_course):
    topic = published_course.chapters[0].topics[0]
    quiz, *_ = _mcq_with_quiz(db_session, published_course.subject, topic)

    student = register(client, "student")
    attempt_id = client.post(f"/api/v1/quizzes/{quiz.id}/attempts", headers=auth_headers(student)).json()["id"]

    first = client.post(f"/api/v1/quiz-attempts/{attempt_id}/submit", json={"answers": []}, headers=auth_headers(student))
    assert first.status_code == 200

    second = client.post(f"/api/v1/quiz-attempts/{attempt_id}/submit", json={"answers": []}, headers=auth_headers(student))
    assert second.status_code == 409


def test_quiz_detail_never_reveals_correct_option(client, db_session, published_course):
    topic = published_course.chapters[0].topics[0]
    quiz, *_ = _mcq_with_quiz(db_session, published_course.subject, topic)

    res = client.get(f"/api/v1/quizzes/{quiz.id}")
    body = res.text
    assert "is_correct" not in body
    assert "correct_answer" not in body
