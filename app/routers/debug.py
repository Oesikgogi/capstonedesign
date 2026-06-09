from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .character import get_or_create_my_character, serialize_my_character
from .user import get_current_admin_user

router = APIRouter(prefix="/debug", tags=["debug"])


def get_or_create_preference(db: Session, user_id: int) -> models.UserPreference:
    preference = (
        db.query(models.UserPreference)
        .filter(models.UserPreference.user_id == user_id)
        .first()
    )
    if preference:
        return preference

    preference = models.UserPreference(user_id=user_id)
    db.add(preference)
    db.flush()
    return preference


def clear_user_quiz_history(db: Session, user: models.User) -> None:
    db.query(models.UserQuizConnect).filter(
        models.UserQuizConnect.user_id == user.user_id,
    ).delete(synchronize_session=False)


def clear_user_meal_history(
    db: Session,
    user: models.User,
    character: models.Character,
) -> None:
    db.query(models.SchoolFoodFeed).filter(
        models.SchoolFoodFeed.user_id == user.user_id,
    ).delete(synchronize_session=False)
    character.skipped_meal_count = 0
    character.applied_penalty_count = 0
    character.hungry_state = False
    character.meal_health_date = None
    character.last_checked_meal_slot = None


def reset_user_game_state(
    db: Session,
    user: models.User,
    character: models.Character,
) -> None:
    clear_user_quiz_history(db, user)
    clear_user_meal_history(db, user, character)
    db.query(models.MiniGameResult).filter(
        models.MiniGameResult.user_id == user.user_id,
    ).delete(synchronize_session=False)
    db.query(models.MiniGamePlaySession).filter(
        models.MiniGamePlaySession.user_id == user.user_id,
    ).delete(synchronize_session=False)
    db.query(models.UserAchievement).filter(
        models.UserAchievement.user_id == user.user_id,
    ).delete(synchronize_session=False)
    db.query(models.UserAchievementCounter).filter(
        models.UserAchievementCounter.user_id == user.user_id,
    ).delete(synchronize_session=False)
    db.query(models.UserRoomEquipped).filter(
        models.UserRoomEquipped.user_id == user.user_id,
    ).delete(synchronize_session=False)
    db.query(models.UserRoomItem).filter(
        models.UserRoomItem.user_id == user.user_id,
    ).delete(synchronize_session=False)
    db.query(models.UserSkin).filter(
        models.UserSkin.user_id == user.user_id,
    ).delete(synchronize_session=False)
    db.query(models.Friend).filter(
        (models.Friend.user_id == user.user_id)
        | (models.Friend.friend_user_id == user.user_id),
    ).delete(synchronize_session=False)
    db.query(models.FriendRequest).filter(
        (models.FriendRequest.requester_id == user.user_id)
        | (models.FriendRequest.receiver_id == user.user_id),
    ).delete(synchronize_session=False)

    user.coin = 100
    user.xp_point = 0
    user.heart = 5
    user.heart_updated_at = datetime.utcnow()
    user.graduated_at = None
    character.stage = 1
    character.state = "basic1"
    character.equipped_skin_key = "default"
    character.pending_evolution = False


@router.patch("/me", response_model=schemas.DebugMeResult)
def patch_my_debug_state(
    patch_in: schemas.DebugMePatch,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    character = get_or_create_my_character(db, current_admin)
    update_data = patch_in.dict(exclude_unset=True)

    if update_data.get("reset_game_state") is True:
        reset_user_game_state(db, current_admin, character)
    if update_data.get("clear_quiz_history") is True:
        clear_user_quiz_history(db, current_admin)
    if update_data.get("clear_meal_history") is True:
        clear_user_meal_history(db, current_admin, character)

    if "name" in update_data and update_data["name"] is not None:
        current_admin.name = update_data["name"].strip()
    if "student_id" in update_data and update_data["student_id"] is not None:
        current_admin.student_id = update_data["student_id"].strip()
    if "character_name" in update_data and update_data["character_name"] is not None:
        character.character_name = update_data["character_name"].strip()
    if "coin" in update_data and update_data["coin"] is not None:
        current_admin.coin = max(update_data["coin"], 0)
    if "xp_point" in update_data and update_data["xp_point"] is not None:
        current_admin.xp_point = max(update_data["xp_point"], 0)
    if "stage" in update_data and update_data["stage"] is not None:
        character.stage = max(update_data["stage"], 1)
    if "character_state" in update_data and update_data["character_state"] is not None:
        character.state = update_data["character_state"]
    if "skipped_meal_count" in update_data and update_data["skipped_meal_count"] is not None:
        character.skipped_meal_count = max(update_data["skipped_meal_count"], 0)
        character.hungry_state = character.skipped_meal_count >= 6

    preference_patch = {
        key: update_data[key]
        for key in (
            "has_seen_game_tutorial",
            "has_seen_minigame_tutorial",
            "meal_day_mode",
            "meal_restriction_enabled",
            "quiz_daily_limit_enabled",
        )
        if key in update_data and update_data[key] is not None
    }
    if preference_patch:
        preference = get_or_create_preference(db, current_admin.user_id)
        for key, value in preference_patch.items():
            setattr(preference, key, value)
        preference.updated_at = datetime.utcnow()

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Debug patch conflicts with an existing unique value",
        ) from error

    db.refresh(current_admin)
    db.refresh(character)
    return {
        "user": current_admin,
        "character": serialize_my_character(character, current_admin),
    }
