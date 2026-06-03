from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.achievements import apply_achievement_event, evaluate_achievements
from ..core.errors import error_detail
from ..database import get_db
from .user import get_current_admin_user, get_current_user

router = APIRouter(prefix="/quizzes", tags=["quizzes"])

QUIZ_CORRECT_XP = 30
QUIZ_INCORRECT_XP = -10
QUIZ_COIN_REWARD = 10
QUIZ_DAILY_LIMIT = 3
QUIZ_COOLDOWN_HOURS = 3
KST = ZoneInfo("Asia/Seoul")


def get_kst_now() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)


def normalize_answer(answer: str) -> str:
    normalized = answer.strip().casefold()
    if normalized.endswith(")"):
        normalized = normalized[:-1].strip()
    return normalized


def has_user_solved_quiz(db: Session, user_id: int, quiz_id: int) -> bool:
    return (
        db.query(models.UserQuizConnect)
        .filter(
            models.UserQuizConnect.user_id == user_id,
            models.UserQuizConnect.quiz_id == quiz_id,
        )
        .first()
        is not None
    )


def get_quiz_play_status(db: Session, user_id: int, now: datetime) -> dict:
    today_start = datetime.combine(now.date(), time.min)
    tomorrow_start = today_start + timedelta(days=1)
    solved_today = (
        db.query(models.UserQuizConnect)
        .filter(
            models.UserQuizConnect.user_id == user_id,
            models.UserQuizConnect.user_quiz_time >= today_start,
            models.UserQuizConnect.user_quiz_time < tomorrow_start,
        )
        .count()
    )
    last_play = (
        db.query(models.UserQuizConnect)
        .filter(models.UserQuizConnect.user_id == user_id)
        .order_by(models.UserQuizConnect.user_quiz_time.desc())
        .first()
    )
    last_played_at = last_play.user_quiz_time if last_play else None
    next_available_at = (
        last_played_at + timedelta(hours=QUIZ_COOLDOWN_HOURS)
        if last_played_at
        else None
    )
    cooldown_ready = next_available_at is None or now >= next_available_at
    remaining_today = max(QUIZ_DAILY_LIMIT - solved_today, 0)
    blocked_reason = None
    if remaining_today <= 0:
        blocked_reason = "daily_limit"
    elif not cooldown_ready:
        blocked_reason = "cooldown"

    return {
        "date": now.date().isoformat(),
        "solved_today": solved_today,
        "daily_limit": QUIZ_DAILY_LIMIT,
        "remaining_today": remaining_today,
        "cooldown_hours": QUIZ_COOLDOWN_HOURS,
        "last_played_at": last_played_at,
        "next_available_at": next_available_at,
        "can_play_now": remaining_today > 0 and cooldown_ready,
        "blocked_reason": blocked_reason,
    }


@router.post("/", response_model=schemas.Quiz)
def create_quiz(
    quiz_in: schemas.QuizCreate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    quiz = models.Quiz(**quiz_in.dict())
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


@router.get("/", response_model=list[schemas.Quiz])
def list_quizzes(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    return db.query(models.Quiz).all()


@router.get("/available", response_model=list[schemas.QuizQuestion])
def list_available_quizzes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    solved_quiz_ids = select(models.UserQuizConnect.quiz_id).filter(
        models.UserQuizConnect.user_id == current_user.user_id
    )
    return (
        db.query(models.Quiz)
        .filter(models.Quiz.quiz_id.notin_(solved_quiz_ids))
        .order_by(models.Quiz.quiz_id)
        .all()
    )


@router.get("/next", response_model=schemas.QuizQuestion)
def get_next_quiz(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    solved_quiz_ids = select(models.UserQuizConnect.quiz_id).filter(
        models.UserQuizConnect.user_id == current_user.user_id
    )
    quiz = (
        db.query(models.Quiz)
        .filter(models.Quiz.quiz_id.notin_(solved_quiz_ids))
        .order_by(models.Quiz.quiz_id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No unsolved quizzes available")
    return quiz


@router.get("/play-status", response_model=schemas.QuizPlayStatus)
def read_quiz_play_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return get_quiz_play_status(db, current_user.user_id, get_kst_now())


@router.post("/submit", response_model=schemas.QuizSubmitResult)
def submit_quiz(
    submit_in: schemas.QuizSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    now = get_kst_now()
    play_status = get_quiz_play_status(db, current_user.user_id, now)
    if play_status["remaining_today"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail("DAILY_LIMIT_EXCEEDED", "오늘 풀 수 있는 퀴즈를 모두 풀었습니다."),
        )
    if not play_status["can_play_now"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                "QUIZ_COOLDOWN",
                "퀴즈 쿨타임이 아직 끝나지 않았습니다.",
                {"next_available_at": play_status["next_available_at"]},
            ),
        )

    quiz = db.query(models.Quiz).filter(models.Quiz.quiz_id == submit_in.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    if has_user_solved_quiz(db, current_user.user_id, quiz.quiz_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quiz already solved by this user")

    correct = normalize_answer(submit_in.answer) == normalize_answer(quiz.answer)
    awarded_points = QUIZ_CORRECT_XP if correct else QUIZ_INCORRECT_XP
    current_user.xp_point += awarded_points
    current_user.coin += QUIZ_COIN_REWARD

    solved_record = models.UserQuizConnect(
        user_id=current_user.user_id,
        quiz_id=quiz.quiz_id,
        correct_boolean=correct,
        user_quiz_time=now,
    )
    db.add(solved_record)
    unlocked_achievements = (
        apply_achievement_event(db, current_user, "quiz_correct")
        if correct
        else evaluate_achievements(db, current_user)
    )
    db.commit()
    db.refresh(current_user)

    return {
        "detail": "Correct answer" if correct else "Incorrect answer",
        "correct": correct,
        "awarded_points": awarded_points,
        "awarded_coin": QUIZ_COIN_REWARD,
        "xp_point": current_user.xp_point,
        "coin": current_user.coin,
        "correct_answer": quiz.answer,
        "unlocked_achievements": unlocked_achievements,
    }


@router.get("/{quiz_id}", response_model=schemas.Quiz)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    quiz = db.query(models.Quiz).filter(models.Quiz.quiz_id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


@router.put("/{quiz_id}", response_model=schemas.Quiz)
def update_quiz(
    quiz_id: int,
    quiz_in: schemas.QuizUpdate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    quiz = db.query(models.Quiz).filter(models.Quiz.quiz_id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    for field, value in quiz_in.dict(exclude_unset=True).items():
        setattr(quiz, field, value)
    db.commit()
    db.refresh(quiz)
    return quiz


@router.delete("/{quiz_id}")
def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    quiz = db.query(models.Quiz).filter(models.Quiz.quiz_id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    db.delete(quiz)
    db.commit()
    return {"detail": "Quiz deleted"}
