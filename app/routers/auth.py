from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenWithRefresh)
def login(login_in: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == login_in.email).first()
    if not user or not verify_password(login_in.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.user_id), "email": user.email},
        expires_delta=timedelta(minutes=60),
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.user_id), "email": user.email}
    )

    refresh_payload = decode_token(refresh_token)
    db_token = models.RefreshToken(
        token=refresh_token,
        user_id=user.user_id,
        expires_at=datetime.utcfromtimestamp(refresh_payload["exp"]),
    )
    db.add(db_token)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
    }


@router.post("/refresh", response_model=schemas.TokenWithRefresh)
def refresh_token(refresh_in: schemas.RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_in.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token type")

    token_record = db.query(models.RefreshToken).filter(models.RefreshToken.token == refresh_in.refresh_token).first()
    if not token_record or token_record.revoked or token_record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or expired")

    user = db.query(models.User).filter(models.User.user_id == token_record.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    token_record.revoked = True
    db.commit()

    access_token = create_access_token(
        data={"sub": str(user.user_id), "email": user.email},
        expires_delta=timedelta(minutes=60),
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.user_id), "email": user.email}
    )
    new_refresh_payload = decode_token(new_refresh_token)
    db_token = models.RefreshToken(
        token=new_refresh_token,
        user_id=user.user_id,
        expires_at=datetime.utcfromtimestamp(new_refresh_payload["exp"]),
    )
    db.add(db_token)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": new_refresh_token,
    }
