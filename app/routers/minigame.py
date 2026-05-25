from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .user import get_current_user

router = APIRouter(prefix="/minigames", tags=["minigames"])


@router.post("/results", response_model=schemas.MiniGameResultOut)
def create_minigame_result(
    result_in: schemas.MiniGameResultCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = models.MiniGameResult(
        user_id=current_user.user_id,
        game_type=result_in.game_type,
        location=result_in.location,
        score=result_in.score,
        success=result_in.success,
        play_time_seconds=result_in.play_time_seconds,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@router.get("/results/me", response_model=list[schemas.MiniGameResultOut])
def list_my_minigame_results(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.MiniGameResult)
        .filter(models.MiniGameResult.user_id == current_user.user_id)
        .order_by(models.MiniGameResult.created_at.desc())
        .all()
    )


@router.get("/ranking/me", response_model=schemas.MiniGameRankingMe)
def get_my_minigame_ranking(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    best_scores = (
        db.query(
            models.MiniGameResult.user_id.label("user_id"),
            func.max(models.MiniGameResult.score).label("best_score"),
        )
        .group_by(models.MiniGameResult.user_id)
        .subquery()
    )

    my_best_score = (
        db.query(best_scores.c.best_score)
        .filter(best_scores.c.user_id == current_user.user_id)
        .scalar()
    )
    total_ranked_users = db.query(best_scores.c.user_id).count()
    total_users = db.query(models.User).count()

    if my_best_score is None:
        return {
            "rank": None,
            "best_score": None,
            "total_ranked_users": total_ranked_users,
            "total_users": total_users,
        }

    users_with_higher_score = (
        db.query(best_scores.c.user_id)
        .filter(best_scores.c.best_score > my_best_score)
        .count()
    )

    return {
        "rank": users_with_higher_score + 1,
        "best_score": my_best_score,
        "total_ranked_users": total_ranked_users,
        "total_users": total_users,
    }
