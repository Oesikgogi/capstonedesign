from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .economy import (
    HEART_RECHARGE_MINUTES,
    MAX_HEART,
    MINIGAME_COIN_REWARD,
    MINIGAME_HEART_COST,
    get_kst_now,
    serialize_economy_status,
    sync_user_hearts,
)
from .quiz import (
    QUIZ_COIN_REWARD,
    QUIZ_COOLDOWN_HOURS,
    QUIZ_CORRECT_XP,
    QUIZ_DAILY_LIMIT,
    QUIZ_INCORRECT_XP,
)
from .room import serialize_room
from .school_food import FEED_COIN_COST, FEED_XP
from .shop import serialize_shop_item
from .user import get_current_user

router = APIRouter(prefix="/app", tags=["app"])


@router.get("/config", response_model=schemas.AppConfig)
def get_app_config():
    return {
        "quiz": {
            "daily_limit": QUIZ_DAILY_LIMIT,
            "cooldown_hours": QUIZ_COOLDOWN_HOURS,
            "correct_xp": QUIZ_CORRECT_XP,
            "incorrect_xp": QUIZ_INCORRECT_XP,
            "reward_coin": QUIZ_COIN_REWARD,
        },
        "minigame": {
            "max_heart": MAX_HEART,
            "heart_recovery_minutes": HEART_RECHARGE_MINUTES,
            "reward_coin": MINIGAME_COIN_REWARD,
            "heart_cost": MINIGAME_HEART_COST,
        },
        "school_food": {
            "feed_xp": FEED_XP,
            "feed_coin_cost": FEED_COIN_COST,
        },
    }


@router.get("/bootstrap", response_model=schemas.AppBootstrap)
def get_app_bootstrap(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = get_kst_now()
    sync_user_hearts(current_user, now)
    db.commit()
    db.refresh(current_user)

    character = (
        db.query(models.Character)
        .filter(models.Character.user_id == current_user.user_id)
        .order_by(models.Character.character_id.asc())
        .first()
    )
    equipped_items = (
        db.query(models.UserRoomEquipped)
        .filter(models.UserRoomEquipped.user_id == current_user.user_id)
        .order_by(models.UserRoomEquipped.item_type)
        .all()
    )

    owned_item_ids = {
        row.item_id
        for row in db.query(models.UserRoomItem.item_id)
        .filter(models.UserRoomItem.user_id == current_user.user_id)
        .all()
    }
    equipped_item_ids = {equipped.item_id for equipped in equipped_items}
    shop_items = (
        db.query(models.RoomItem)
        .order_by(models.RoomItem.item_type, models.RoomItem.price, models.RoomItem.item_id)
        .all()
    )
    preference = db.query(models.UserPreference).filter(models.UserPreference.user_id == current_user.user_id).first()

    return {
        "user": current_user,
        "economy": serialize_economy_status(current_user, now),
        "character": character,
        "room": serialize_room(current_user, equipped_items, db),
        "shop_items": [
            serialize_shop_item(item, owned_item_ids, equipped_item_ids)
            for item in shop_items
        ],
        "tutorial_flags": {
            "has_seen_game_tutorial": preference.has_seen_game_tutorial if preference else False,
            "has_seen_minigame_tutorial": preference.has_seen_minigame_tutorial if preference else False,
        },
    }
