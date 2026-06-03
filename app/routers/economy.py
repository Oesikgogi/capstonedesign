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


def get_next_heart_at(user: models.User) -> datetime | None:
    if user.heart is None or user.heart >= MAX_HEART:
        return None
    if user.heart_updated_at is None:
        return None
    return user.heart_updated_at + timedelta(minutes=HEART_RECHARGE_MINUTES)


def serialize_economy_status(user: models.User, now: datetime) -> dict:
    return {
        "coin": user.coin,
        "heart": user.heart,
        "max_heart": MAX_HEART,
        "heart_updated_at": user.heart_updated_at,
        "next_heart_at": get_next_heart_at(user),
        "server_time": now,
    }


@router.get("/status", response_model=schemas.EconomyStatus)
def get_economy_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = get_kst_now()
    sync_user_hearts(current_user, now)
    db.commit()
    db.refresh(current_user)
    return serialize_economy_status(current_user, now)


@router.post("/minigame/start", response_model=schemas.MiniGameStartResult)
def start_minigame(
    start_in: schemas.MiniGameStartRequest,
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
    play_session = models.MiniGamePlaySession(
        user_id=current_user.user_id,
        game_type=start_in.game_type,
        mode=start_in.mode,
        spent_heart=MINIGAME_HEART_COST,
        started_at=now,
    )
    db.add(play_session)
    db.commit()
    db.refresh(current_user)
    db.refresh(play_session)

    return {
        "play_session_id": play_session.play_session_id,
        "spent_heart": MINIGAME_HEART_COST,
        "heart": current_user.heart,
        "max_heart": MAX_HEART,
        "heart_updated_at": current_user.heart_updated_at,
        "next_heart_at": get_next_heart_at(current_user),
    }


@router.post("/minigame/reward", response_model=schemas.MiniGameRewardResult)
def reward_minigame(
    reward_in: schemas.MiniGameRewardRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    play_session = (
        db.query(models.MiniGamePlaySession)
        .filter(
            models.MiniGamePlaySession.play_session_id == reward_in.play_session_id,
            models.MiniGamePlaySession.user_id == current_user.user_id,
        )
        .first()
    )
    if not play_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mini game session not found")
    if play_session.rewarded:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mini game reward already granted")
    if play_session.game_type != reward_in.game_type or play_session.mode != reward_in.mode:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mini game session mismatch")

    play_session.rewarded = True
    play_session.rewarded_at = get_kst_now()
    current_user.coin += MINIGAME_COIN_REWARD

    db.commit()
    db.refresh(current_user)
    return {
        "awarded_coin": MINIGAME_COIN_REWARD,
        "coin": current_user.coin,
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
        "heart_updated_at": current_user.heart_updated_at,
        "next_heart_at": get_next_heart_at(current_user),
    }
