from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .user import get_current_user

router = APIRouter(prefix="/economy", tags=["economy"])

MAX_HEART = 5
HEART_RECHARGE_MINUTES = 30
MINIGAME_COIN_REWARD = 3
MINIGAME_HEART_COST = 1
KST = ZoneInfo("Asia/Seoul")


def get_kst_now() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)


def sync_user_hearts(user: models.User, now: datetime) -> None:
    if user.heart is None:
        user.heart = MAX_HEART
    if user.heart_updated_at is None:
        user.heart_updated_at = now

    user.heart = max(0, min(user.heart, MAX_HEART))
    if user.heart >= MAX_HEART:
        user.heart_updated_at = now
        return

    elapsed = now - user.heart_updated_at
    if elapsed < timedelta(minutes=HEART_RECHARGE_MINUTES):
        return

    recharged_hearts = int(elapsed.total_seconds() // (HEART_RECHARGE_MINUTES * 60))
    if recharged_hearts <= 0:
        return

    user.heart = min(MAX_HEART, user.heart + recharged_hearts)
    if user.heart >= MAX_HEART:
        user.heart_updated_at = now
    else:
        user.heart_updated_at += timedelta(minutes=HEART_RECHARGE_MINUTES * recharged_hearts)


@router.get("/status", response_model=schemas.EconomyStatus)
def get_economy_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sync_user_hearts(current_user, get_kst_now())
    db.commit()
    db.refresh(current_user)
    return {
        "coin": current_user.coin,
        "heart": current_user.heart,
        "max_heart": MAX_HEART,
    }


@router.post("/minigame/play", response_model=schemas.MiniGamePlayResult)
def play_minigame(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = get_kst_now()
    sync_user_hearts(current_user, now)
    if current_user.heart < MINIGAME_HEART_COST:
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough hearts")

    current_user.heart -= MINIGAME_HEART_COST
    current_user.heart_updated_at = now
    current_user.coin += MINIGAME_COIN_REWARD

    db.commit()
    db.refresh(current_user)
    return {
        "detail": "Mini game reward granted",
        "awarded_coin": MINIGAME_COIN_REWARD,
        "spent_heart": MINIGAME_HEART_COST,
        "coin": current_user.coin,
        "heart": current_user.heart,
        "max_heart": MAX_HEART,
    }
