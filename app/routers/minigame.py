from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.achievements import evaluate_achievements
from ..core.errors import error_detail
from ..database import get_db
from .user import get_current_user

router = APIRouter(prefix="/minigames", tags=["minigames"])


def serialize_minigame_result(
    result: models.MiniGameResult,
    unlocked_achievements: Optional[list[dict]] = None,
) -> dict:
    return {
        "result_id": result.result_id,
        "user_id": result.user_id,
        "play_session_id": result.play_session_id,
        "game_type": result.game_type,
        "mode": result.mode,
        "location": result.location,
        "score": result.score,
        "success": result.success,
        "ended_reason": result.ended_reason,
        "play_time_seconds": result.play_time_seconds,
        "created_at": result.created_at,
        "unlocked_achievements": unlocked_achievements or [],
    }


def get_existing_result_by_session(db: Session, play_session_id: str) -> models.MiniGameResult | None:
    return (
        db.query(models.MiniGameResult)
        .filter(models.MiniGameResult.play_session_id == play_session_id)
        .first()
    )


@router.post("/results", response_model=schemas.MiniGameResultOut)
def create_minigame_result(
    result_in: schemas.MiniGameResultCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if result_in.play_session_id:
        existing_result = get_existing_result_by_session(db, result_in.play_session_id)
        if existing_result:
            if existing_result.user_id != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=error_detail("RESULT_ALREADY_EXISTS", "이미 다른 유저의 미니게임 결과로 저장된 세션입니다."),
                )
            return serialize_minigame_result(existing_result)

    result = models.MiniGameResult(
        user_id=current_user.user_id,
        play_session_id=result_in.play_session_id,
        game_type=result_in.game_type,
        mode=result_in.mode,
        location=result_in.location,
        score=result_in.score,
        success=result_in.success,
        ended_reason=result_in.ended_reason,
        play_time_seconds=result_in.play_time_seconds,
    )
    db.add(result)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        if result_in.play_session_id:
            existing_result = get_existing_result_by_session(db, result_in.play_session_id)
            if existing_result and existing_result.user_id == current_user.user_id:
                return serialize_minigame_result(existing_result)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_detail("RESULT_ALREADY_EXISTS", "이미 저장된 미니게임 결과입니다."),
        )

    unlocked_achievements = evaluate_achievements(db, current_user)
    db.commit()
    db.refresh(result)
    return serialize_minigame_result(result, unlocked_achievements)


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


def get_best_scores_subquery(db: Session, game_type: Optional[str], mode: Optional[str]):
    query = db.query(
        models.MiniGameResult.user_id.label("user_id"),
        func.max(models.MiniGameResult.score).label("best_score"),
    )
    if game_type:
        query = query.filter(models.MiniGameResult.game_type == game_type)
    if mode:
        query = query.filter(models.MiniGameResult.mode == mode)
    return query.group_by(models.MiniGameResult.user_id).subquery()


@router.get("/ranking/me", response_model=schemas.MiniGameRankingMe)
def get_my_minigame_ranking(
    game_type: Optional[str] = None,
    mode: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    best_scores = get_best_scores_subquery(db, game_type, mode)
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


def build_ranking_list(
    db: Session,
    best_scores,
    limit: int,
    friend_user_ids: Optional[set[int]] = None,
) -> list[dict]:
    query = (
        db.query(
            models.User.user_id,
            models.User.student_id,
            models.User.nickname,
            models.User.image,
            best_scores.c.best_score,
        )
        .join(best_scores, best_scores.c.user_id == models.User.user_id)
        .order_by(best_scores.c.best_score.desc(), models.User.user_id.asc())
    )
    if friend_user_ids is not None:
        query = query.filter(models.User.user_id.in_(friend_user_ids))

    rows = query.limit(limit).all()
    return [
        {
            "user_id": row.user_id,
            "student_id": row.student_id,
            "nickname": row.nickname,
            "image": row.image,
            "rank": index + 1,
            "best_score": row.best_score,
        }
        for index, row in enumerate(rows)
    ]


@router.get("/rankings", response_model=schemas.MiniGameRankingList)
def list_minigame_rankings(
    game_type: Optional[str] = None,
    mode: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    best_scores = get_best_scores_subquery(db, game_type, mode)
    total_ranked_users = db.query(best_scores.c.user_id).count()
    return {
        "game_type": game_type,
        "mode": mode,
        "total_ranked_users": total_ranked_users,
        "rankings": build_ranking_list(db, best_scores, limit),
    }


@router.get("/rankings/friends", response_model=schemas.MiniGameRankingList)
def list_friend_minigame_rankings(
    game_type: Optional[str] = None,
    mode: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend_user_ids = {
        row.friend_user_id
        for row in db.query(models.Friend.friend_user_id)
        .filter(models.Friend.user_id == current_user.user_id)
        .all()
    }
    friend_user_ids.add(current_user.user_id)

    best_scores = get_best_scores_subquery(db, game_type, mode)
    total_ranked_users = (
        db.query(best_scores.c.user_id)
        .filter(best_scores.c.user_id.in_(friend_user_ids))
        .count()
    )
    return {
        "game_type": game_type,
        "mode": mode,
        "total_ranked_users": total_ranked_users,
        "rankings": build_ranking_list(db, best_scores, limit, friend_user_ids),
    }
