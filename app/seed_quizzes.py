import json
from pathlib import Path

from . import models
from .database import SessionLocal


QUIZ_POINT = 10
QUIZZES_PATH = Path(__file__).resolve().parent / "data" / "quizzes.json"


def seed_quizzes() -> tuple[int, int]:
    quizzes = json.loads(QUIZZES_PATH.read_text(encoding="utf-8"))
    quiz_questions = {quiz_data["question"] for quiz_data in quizzes}
    created = 0
    updated = 0

    db = SessionLocal()
    try:
        db.query(models.UserQuizConnect).filter(
            models.UserQuizConnect.quiz_id.in_(
                db.query(models.Quiz.quiz_id).filter(
                    models.Quiz.question.notin_(quiz_questions)
                )
            )
        ).delete(synchronize_session=False)
        db.query(models.Quiz).filter(
            models.Quiz.question.notin_(quiz_questions)
        ).delete(synchronize_session=False)

        for quiz_data in quizzes:
            quiz = (
                db.query(models.Quiz)
                .filter(models.Quiz.question == quiz_data["question"])
                .first()
            )
            if quiz:
                quiz.options = quiz_data.get("options", ["O", "X"])
                quiz.answer = quiz_data["answer"]
                quiz.quiz_point = QUIZ_POINT
                updated += 1
                continue

            db.add(
                models.Quiz(
                    question=quiz_data["question"],
                    options=quiz_data.get("options", ["O", "X"]),
                    answer=quiz_data["answer"],
                    quiz_point=QUIZ_POINT,
                )
            )
            created += 1

        db.commit()
    finally:
        db.close()

    return created, updated


if __name__ == "__main__":
    created_count, updated_count = seed_quizzes()
    print(f"Created {created_count} quizzes, updated {updated_count} quizzes.")
