from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.achievements import evaluate_achievements
from ..database import get_db
from .user import get_current_admin_user, get_current_user

router = APIRouter(prefix="/characters", tags=["characters"])

KST = ZoneInfo("Asia/Seoul")
EVOLUTION_XP_UNIT = 1000
MEAL_PENALTY_XP = 10
ALLOWED_SKIN_KEYS = {"default", "skin_truth", "skin_peace", "skin_creation"}


def get_kst_now() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)


def get_or_create_my_character(db: Session, user: models.User) -> models.Character:
    character = (
        db.query(models.Character)
        .filter(models.Character.user_id == user.user_id)
        .order_by(models.Character.character_id.asc())
        .first()
    )
    if character:
        return character

    character = models.Character(
        user_id=user.user_id,
        character_name="부",
        stage=1,
        state="basic1",
        equipped_skin_key="default",
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


def serialize_my_character(character: models.Character, user: models.User) -> dict:
    return {
        "character_id": character.character_id,
        "character_name": character.character_name,
        "name": user.name,
        "nickname": user.nickname,
        "stage": character.stage,
        "grade": character.stage,
        "xp_point": user.xp_point,
        "state": character.state,
        "equipped_skin_key": character.equipped_skin_key or "default",
        "pending_evolution": character.pending_evolution,
    }


def validate_skin_ownership(db: Session, user: models.User, skin_key: str) -> None:
    if skin_key not in ALLOWED_SKIN_KEYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid skin key")
    if skin_key == "default":
        return
    owned_skin = (
        db.query(models.UserSkin)
        .filter(
            models.UserSkin.user_id == user.user_id,
            models.UserSkin.skin_key == skin_key,
            models.UserSkin.owned == True,
        )
        .first()
    )
    if not owned_skin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Skin is not owned")


def get_passed_meal_slots(now: datetime) -> list[str]:
    current_time = now.time()
    slots = []
    if current_time >= time(10, 0):
        slots.append("breakfast")
    if current_time >= time(13, 0):
        slots.append("lunch")
    if current_time >= time(19, 0):
        slots.append("dinner")
    return slots


def sync_meal_health(db: Session, character: models.Character, user: models.User, now: datetime) -> dict:
    today = now.date()
    if character.meal_health_date != today:
        character.meal_health_date = today
        character.skipped_meal_count = 0
        character.hungry_state = False
        character.last_checked_meal_slot = None
        character.applied_penalty_count = 0

    fed_slots = {
        row.meal_slot
        for row in db.query(models.SchoolFoodFeed.meal_slot)
        .filter(
            models.SchoolFoodFeed.user_id == user.user_id,
            models.SchoolFoodFeed.feed_date == today,
        )
        .all()
    }
    skipped_slots = [slot for slot in get_passed_meal_slots(now) if slot not in fed_slots]
    character.skipped_meal_count = len(skipped_slots)
    character.hungry_state = character.skipped_meal_count > character.applied_penalty_count
    character.last_checked_meal_slot = skipped_slots[-1] if skipped_slots else None
    return {
        "skipped_meal_count": character.skipped_meal_count,
        "hungry_state": character.hungry_state,
        "last_checked_meal_slot": character.last_checked_meal_slot,
        "applied_penalty_count": character.applied_penalty_count,
        "server_time": now,
    }


@router.get("/me", response_model=schemas.CharacterMeOut)
def get_my_character(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    character = get_or_create_my_character(db, current_user)
    return serialize_my_character(character, current_user)


@router.put("/me", response_model=schemas.CharacterMeOut)
def update_my_character(
    character_in: schemas.CharacterMeUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    character = get_or_create_my_character(db, current_user)
    update_data = character_in.dict(exclude_unset=True)
    if "equipped_skin_key" in update_data:
        skin_key = update_data["equipped_skin_key"] or "default"
        validate_skin_ownership(db, current_user, skin_key)
        update_data["equipped_skin_key"] = skin_key
    for field, value in update_data.items():
        setattr(character, field, value)
    db.commit()
    db.refresh(character)
    return serialize_my_character(character, current_user)


@router.post("/me/xp", response_model=schemas.CharacterXpResult)
def add_my_character_xp(
    xp_in: schemas.CharacterXpRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    character = get_or_create_my_character(db, current_user)
    current_user.xp_point = max(0, current_user.xp_point + xp_in.amount)
    if current_user.xp_point >= character.stage * EVOLUTION_XP_UNIT:
        character.pending_evolution = True
    unlocked_achievements = evaluate_achievements(db, current_user)
    db.commit()
    db.refresh(current_user)
    db.refresh(character)
    return {
        "xp_point": current_user.xp_point,
        "added_xp": xp_in.amount,
        "stage": character.stage,
        "pending_evolution": character.pending_evolution,
        "unlocked_achievements": unlocked_achievements,
    }


@router.post("/me/evolve/confirm", response_model=schemas.CharacterMeOut)
def confirm_my_character_evolution(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    character = get_or_create_my_character(db, current_user)
    if not character.pending_evolution and current_user.xp_point < character.stage * EVOLUTION_XP_UNIT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evolution is not available")

    character.stage += 1
    character.state = f"basic{character.stage}"
    character.pending_evolution = False
    db.commit()
    db.refresh(character)
    return serialize_my_character(character, current_user)


@router.get("/me/meal-health", response_model=schemas.CharacterMealHealth)
def get_my_character_meal_health(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    character = get_or_create_my_character(db, current_user)
    status_data = sync_meal_health(db, character, current_user, get_kst_now())
    db.commit()
    return status_data


@router.post("/me/meal-penalty/apply", response_model=schemas.CharacterMealPenaltyResult)
def apply_my_character_meal_penalty(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    character = get_or_create_my_character(db, current_user)
    now = get_kst_now()
    status_data = sync_meal_health(db, character, current_user, now)
    pending_penalty_count = max(character.skipped_meal_count - character.applied_penalty_count, 0)
    applied_penalty = pending_penalty_count * MEAL_PENALTY_XP
    if applied_penalty:
        current_user.xp_point = max(0, current_user.xp_point - applied_penalty)
        character.applied_penalty_count += pending_penalty_count
        character.hungry_state = False

    db.commit()
    db.refresh(current_user)
    db.refresh(character)
    unlocked_achievements = evaluate_achievements(db, current_user)
    status_data = sync_meal_health(db, character, current_user, now)
    status_data.update({
        "applied_penalty": applied_penalty,
        "xp_point": current_user.xp_point,
        "unlocked_achievements": unlocked_achievements,
    })
    db.commit()
    return status_data


@router.post("/", response_model=schemas.Character)
def create_character(
    character_in: schemas.CharacterCreate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    character = models.Character(**character_in.dict())
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


@router.get("/", response_model=list[schemas.Character])
def list_characters(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    return db.query(models.Character).all()


@router.get("/{character_id}", response_model=schemas.Character)
def get_character(
    character_id: int,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    character = db.query(models.Character).filter(models.Character.character_id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.put("/{character_id}", response_model=schemas.Character)
def update_character(
    character_id: int,
    character_in: schemas.CharacterUpdate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    character = db.query(models.Character).filter(models.Character.character_id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    for field, value in character_in.dict(exclude_unset=True).items():
        setattr(character, field, value)
    db.commit()
    db.refresh(character)
    return character


@router.delete("/{character_id}")
def delete_character(
    character_id: int,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    character = db.query(models.Character).filter(models.Character.character_id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    db.delete(character)
    db.commit()
    return {"detail": "Character deleted"}
