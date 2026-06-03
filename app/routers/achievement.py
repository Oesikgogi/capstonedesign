from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.achievements import (
    ACHIEVEMENTS,
    apply_achievement_event,
    get_user_achievement_progress,
    serialize_achievement_definition,
)
from ..database import get_db
from .user import get_current_user

router = APIRouter(prefix="/achievements", tags=["achievements"])

SUPPORTED_EVENT_TYPES = {
    "room_enter",
    "campus_visit",
}


@router.get("/", response_model=list[schemas.AchievementMaster])
def list_achievements():
    return [serialize_achievement_definition(achievement) for achievement in ACHIEVEMENTS]


@router.get("/me", response_model=list[schemas.AchievementProgress])
def list_my_achievements(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    achievements = get_user_achievement_progress(db, current_user)
    db.commit()
    return achievements


@router.post("/events", response_model=schemas.AchievementEventResult)
def create_achievement_event(
    event_in: schemas.AchievementEventRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if event_in.event_type not in SUPPORTED_EVENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported achievement event")

    event_type = "room_enter" if event_in.event_type == "room_enter" else "campus_visit"
    unlocked_achievements = apply_achievement_event(db, current_user, event_type)
    db.commit()
    db.refresh(current_user)
    return {
        "event_type": event_in.event_type,
        "coin": current_user.coin,
        "xp_point": current_user.xp_point,
        "unlocked_achievements": unlocked_achievements,
    }
