from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .user import get_current_user

router = APIRouter(prefix="/school-foods", tags=["school-foods"])

FEED_XP = 50
FEED_COIN_COST = 4
KST = ZoneInfo("Asia/Seoul")


def get_kst_now() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)


def get_meal_slot(now: datetime) -> Optional[str]:
    current_time = now.time()
    if time(8, 0) <= current_time < time(10, 0):
        return "breakfast"
    if time(11, 0) <= current_time < time(13, 0):
        return "lunch"
    if time(17, 0) <= current_time < time(19, 0):
        return "dinner"
    return None


def get_today_food_type(now: datetime) -> str:
    return "weekend" if now.weekday() >= 5 else "weekday"


@router.post("/", response_model=schemas.SchoolFood)
def create_school_food(item_in: schemas.SchoolFoodCreate, db: Session = Depends(get_db)):
    item = models.SchoolFood(**item_in.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/", response_model=list[schemas.SchoolFood])
def list_school_foods(type: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.SchoolFood)
    if type:
        query = query.filter(models.SchoolFood.type == type)
    return query.order_by(models.SchoolFood.school_food_id).all()


@router.get("/today", response_model=list[schemas.SchoolFood])
def list_today_school_foods(db: Session = Depends(get_db)):
    food_type = get_today_food_type(get_kst_now())
    return (
        db.query(models.SchoolFood)
        .filter(models.SchoolFood.type == food_type)
        .order_by(models.SchoolFood.school_food_id)
        .all()
    )


@router.get("/feed-status", response_model=schemas.SchoolFoodFeedStatus)
def get_school_food_feed_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    now = get_kst_now()
    today = now.date()
    current_slot = get_meal_slot(now)
    fed_slots = [
        item.meal_slot
        for item in (
            db.query(models.SchoolFoodFeed)
            .filter(
                models.SchoolFoodFeed.user_id == current_user.user_id,
                models.SchoolFoodFeed.feed_date == today,
            )
            .order_by(models.SchoolFoodFeed.fed_at)
            .all()
        )
    ]

    return {
        "date": today.isoformat(),
        "current_slot": current_slot,
        "fed_slots": fed_slots,
        "can_feed_now": current_slot is not None and current_slot not in fed_slots,
    }


@router.post("/feed", response_model=schemas.SchoolFoodFeedResult)
def feed_school_food(
    feed_in: schemas.SchoolFoodFeedRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    now = get_kst_now()
    meal_slot = get_meal_slot(now)
    if meal_slot is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="School food can be fed only during breakfast, lunch, or dinner time",
        )

    school_food = (
        db.query(models.SchoolFood)
        .filter(models.SchoolFood.school_food_id == feed_in.school_food_id)
        .first()
    )
    if not school_food:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School food not found")

    expected_type = get_today_food_type(now)
    if school_food.type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This food is not available today",
        )

    today = now.date()
    existing_feed = (
        db.query(models.SchoolFoodFeed)
        .filter(
            models.SchoolFoodFeed.user_id == current_user.user_id,
            models.SchoolFoodFeed.feed_date == today,
            models.SchoolFoodFeed.meal_slot == meal_slot,
        )
        .first()
    )
    if existing_feed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This meal slot has already been fed today",
        )

    if current_user.coin < FEED_COIN_COST:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough coins")

    current_user.xp_point += FEED_XP
    current_user.coin -= FEED_COIN_COST
    feed_record = models.SchoolFoodFeed(
        user_id=current_user.user_id,
        school_food_id=school_food.school_food_id,
        meal_slot=meal_slot,
        feed_date=today,
        fed_at=now,
        awarded_xp=FEED_XP,
    )
    db.add(feed_record)
    db.commit()
    db.refresh(feed_record)
    db.refresh(current_user)

    return {
        "detail": "School food fed successfully",
        "feed_id": feed_record.feed_id,
        "school_food_id": school_food.school_food_id,
        "meal_slot": meal_slot,
        "awarded_xp": FEED_XP,
        "spent_coin": FEED_COIN_COST,
        "xp_point": current_user.xp_point,
        "coin": current_user.coin,
        "fed_at": feed_record.fed_at,
    }


@router.get("/{school_food_id}", response_model=schemas.SchoolFood)
def get_school_food(school_food_id: int, db: Session = Depends(get_db)):
    item = db.query(models.SchoolFood).filter(models.SchoolFood.school_food_id == school_food_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="School food not found")
    return item


@router.put("/{school_food_id}", response_model=schemas.SchoolFood)
def update_school_food(school_food_id: int, item_in: schemas.SchoolFoodUpdate, db: Session = Depends(get_db)):
    item = db.query(models.SchoolFood).filter(models.SchoolFood.school_food_id == school_food_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="School food not found")
    for field, value in item_in.dict(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{school_food_id}")
def delete_school_food(school_food_id: int, db: Session = Depends(get_db)):
    item = db.query(models.SchoolFood).filter(models.SchoolFood.school_food_id == school_food_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="School food not found")
    db.delete(item)
    db.commit()
    return {"detail": "School food deleted"}
