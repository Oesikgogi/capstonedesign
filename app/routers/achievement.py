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
    "first_login": "first_login",
    "room_enter": "room_enter",
    "room_first_enter": "room_enter",
    "campus_visit": "campus_visit",
    "campus_first_visit": "campus_visit",
}

ACCEPTED_NOOP_EVENT_TYPES = {
    # Room equip counts are applied by the authoritative /rooms/me/equip API.
    # Keep this frontend legacy event accepted so duplicate client-side sync calls
    # do not fail or double-count the same equip action.
    "room_item_equip_count",
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
    event_type = SUPPORTED_EVENT_TYPES.get(event_in.event_type)
    if not event_type and event_in.event_type not in ACCEPTED_NOOP_EVENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported achievement event")

    unlocked_achievements = (
        apply_achievement_event(db, current_user, event_type)
        if event_type
        else []
    )
    db.commit()
    db.refresh(current_user)
    return {
        "event_type": event_in.event_type,
        "coin": current_user.coin,
        "xp_point": current_user.xp_point,
        "unlocked_achievements": unlocked_achievements,
    }
