from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .user import get_current_user

router = APIRouter(prefix="/graduation", tags=["graduation"])


def build_graduation_summary(user: models.User, db: Session) -> dict:
    today = datetime.utcnow().date()
    play_days = 1
    if user.created_at:
        play_days = max((today - user.created_at.date()).days + 1, 1)

    best_scores = (
        db.query(
            models.MiniGameResult.game_type,
            models.MiniGameResult.mode,
            func.max(models.MiniGameResult.score).label("best_score"),
        )
        .filter(models.MiniGameResult.user_id == user.user_id)
        .group_by(models.MiniGameResult.game_type, models.MiniGameResult.mode)
        .all()
    )

    return {
        "user_id": user.user_id,
        "created_at": user.created_at,
        "graduated_at": user.graduated_at,
        "play_days": play_days,
        "feed_count": db.query(models.SchoolFoodFeed).filter(models.SchoolFoodFeed.user_id == user.user_id).count(),
        "quiz_attempt_count": db.query(models.UserQuizConnect).filter(models.UserQuizConnect.user_id == user.user_id).count(),
        "quiz_correct_count": db.query(models.UserQuizConnect)
        .filter(
            models.UserQuizConnect.user_id == user.user_id,
            models.UserQuizConnect.correct_boolean == True,
        )
        .count(),
        "minigame_best_scores": [
            {
                "game_type": row.game_type,
                "mode": row.mode,
                "best_score": row.best_score,
            }
            for row in best_scores
        ],
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
