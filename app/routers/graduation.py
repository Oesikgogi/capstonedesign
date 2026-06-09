from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .user import get_current_user

router = APIRouter(prefix="/graduation", tags=["graduation"])

KST = ZoneInfo("Asia/Seoul")
GRADUATION_MINIGAME_TYPES = ("catchTheMajor", "catchBoo", "freeThrow")


def get_kst_today():
    return datetime.now(KST).date()


def get_kst_date(value: datetime):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(KST).date()


def get_play_days(user: models.User) -> int:
    if not user.created_at:
        return 1
    return max((get_kst_today() - get_kst_date(user.created_at)).days + 1, 1)


def get_feed_count(db: Session, user: models.User) -> int:
    return (
        db.query(models.SchoolFoodFeed)
        .filter(models.SchoolFoodFeed.user_id == user.user_id)
        .count()
    )


def get_quiz_attempt_count(db: Session, user: models.User) -> int:
    return (
        db.query(models.UserQuizConnect)
        .filter(models.UserQuizConnect.user_id == user.user_id)
        .count()
    )


def get_quiz_correct_count(db: Session, user: models.User) -> int:
    return (
        db.query(models.UserQuizConnect)
        .filter(
            models.UserQuizConnect.user_id == user.user_id,
            models.UserQuizConnect.correct_boolean == True,
        )
        .count()
    )


def get_minigame_best_scores(db: Session, user: models.User) -> list[dict]:
    best_scores = (
        db.query(
            models.MiniGameResult.game_type,
            func.max(models.MiniGameResult.score).label("best_score"),
        )
        .filter(
            models.MiniGameResult.user_id == user.user_id,
            models.MiniGameResult.game_type.in_(GRADUATION_MINIGAME_TYPES),
            models.MiniGameResult.mode == "normal",
        )
        .group_by(models.MiniGameResult.game_type)
        .order_by(models.MiniGameResult.game_type)
        .all()
    )

    return [
        {
            "game_type": row.game_type,
            "mode": "normal",
            "best_score": row.best_score or 0,
        }
        for row in best_scores
    ]


def build_graduation_summary(user: models.User, db: Session) -> dict:
    return {
        "user_id": user.user_id,
        "created_at": user.created_at,
        "graduated_at": user.graduated_at,
        "play_days": get_play_days(user),
        "feed_count": get_feed_count(db, user),
        "quiz_attempt_count": get_quiz_attempt_count(db, user),
        "quiz_correct_count": get_quiz_correct_count(db, user),
        "minigame_best_scores": get_minigame_best_scores(db, user),
    }


@router.get("/summary", response_model=schemas.GraduationSummary)
def get_graduation_summary(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_graduation_summary(current_user, db)


@router.post("/confirm", response_model=schemas.GraduationSummary)
def confirm_graduation(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.graduated_at is None:
        current_user.graduated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
    return build_graduation_summary(current_user, db)
