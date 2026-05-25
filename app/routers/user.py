import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.email import (
    is_email_delivery_configured,
    send_signup_verification_code,
    send_password_reset,
)
from ..core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    EMAIL_VERIFICATION_EXPIRE_HOURS,
    PASSWORD_RESET_EXPIRE_HOURS,
)
from ..database import get_db

router = APIRouter(prefix="/user", tags=["user"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")


def validate_student_id(student_id: str) -> bool:
    """학번이 9자리 숫자인지 확인"""
    return student_id.isdigit() and len(student_id) == 9


def normalize_email(email: str) -> str:
    return email.lower()


def validate_school_email(email: str) -> bool:
    return normalize_email(email).endswith("@hufs.ac.kr")


def create_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def get_verified_signup_email(email: str, db: Session) -> models.SignupEmailVerification | None:
    return (
        db.query(models.SignupEmailVerification)
        .filter(
            models.SignupEmailVerification.email == normalize_email(email),
            models.SignupEmailVerification.verified == True,
            models.SignupEmailVerification.expires_at >= datetime.utcnow(),
        )
        .order_by(models.SignupEmailVerification.created_at.desc())
        .first()
    )


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(models.User).filter(models.User.user_id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email verification required")
    return user


@router.post("/signup/email", response_model=schemas.SignupEmailVerificationOut)
def request_signup_email_verification(
    request_in: schemas.SignupEmailRequest, db: Session = Depends(get_db)
):
    email = normalize_email(str(request_in.email))
    if not validate_school_email(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email must end with @hufs.ac.kr")

    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    db.query(models.SignupEmailVerification).filter(
        models.SignupEmailVerification.email == email,
        models.SignupEmailVerification.verified == False,
    ).delete()

    verification_code = create_verification_code()
    verification = models.SignupEmailVerification(
        email=email,
        code=verification_code,
        expires_at=datetime.utcnow() + timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS),
    )
    db.add(verification)
    db.commit()

    try:
        email_sent = send_signup_verification_code(email, verification_code)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

    return {
        "detail": "Verification code sent" if email_sent else "Verification code created",
        "verification_code": None if is_email_delivery_configured() else verification_code,
    }


@router.post("/signup/verify")
def verify_signup_email(
    verify_in: schemas.SignupEmailVerificationRequest, db: Session = Depends(get_db)
):
    email = normalize_email(str(verify_in.email))
    verification = (
        db.query(models.SignupEmailVerification)
        .filter(
            models.SignupEmailVerification.email == email,
            models.SignupEmailVerification.code == verify_in.code,
            models.SignupEmailVerification.verified == False,
        )
        .order_by(models.SignupEmailVerification.created_at.desc())
        .first()
    )

    if not verification or verification.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code")

    verification.verified = True
    db.commit()

    return {"detail": "Email verified successfully"}


@router.post("/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    # 학번 검증
    if not validate_student_id(user_in.student_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student ID must be 9 digits")

    # 이메일 검증
    email = normalize_email(str(user_in.email))
    if not validate_school_email(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email must end with @hufs.ac.kr")

    if not get_verified_signup_email(email, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email verification required")

    # 중복 검증
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    if db.query(models.User).filter(models.User.student_id == user_in.student_id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student ID already registered")

    if db.query(models.User).filter(models.User.nickname == user_in.nickname).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nickname already taken")

    # 사용자 생성
    hashed_password = get_password_hash(user_in.password)
    user_data = user_in.dict(exclude={"password"})
    user_data["email"] = email
    user = models.User(
        **user_data,
        password=hashed_password,
        xp_point=0,
        email_verified=True,
        email_verified_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=schemas.TokenWithRefresh)
def login(login_in: schemas.UserLogin, db: Session = Depends(get_db)):
    # 학번으로 사용자 조회
    user = db.query(models.User).filter(models.User.student_id == login_in.student_id).first()
    if not user or not verify_password(login_in.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )

    # 토큰 생성
    access_token = create_access_token(
        data={"sub": str(user.user_id), "student_id": user.student_id},
        expires_delta=timedelta(minutes=60),
    )

    # remember_me가 True면 refresh token 만료 시간 연장
    refresh_expires = timedelta(days=90) if login_in.remember_me else timedelta(days=30)
    refresh_token = create_refresh_token(
        data={"sub": str(user.user_id), "student_id": user.student_id},
        expires_delta=refresh_expires,
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


@router.post("/password-reset-request")
def request_password_reset(request_in: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.student_id == request_in.student_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 기존 미사용 토큰 폐기
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.user_id,
        models.PasswordResetToken.used == False,
    ).delete()

    # 새 리셋 토큰 생성
    reset_token = create_password_reset_token(user.user_id)
    token_expires = datetime.utcnow() + timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS)
    password_token = models.PasswordResetToken(
        token=reset_token,
        user_id=user.user_id,
        expires_at=token_expires,
    )
    db.add(password_token)
    db.commit()

    try:
        email_sent = send_password_reset(user.email, reset_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email",
        )

    response = {"detail": "Password reset email sent" if email_sent else "Password reset token created"}
    if not is_email_delivery_configured():
        response["token"] = reset_token
    return response


@router.post("/password-reset-confirm")
def reset_password(reset_in: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    token_record = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == reset_in.token
    ).first()

    if not token_record or token_record.used or token_record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user = db.query(models.User).filter(models.User.user_id == token_record.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.password = get_password_hash(reset_in.new_password)
    token_record.used = True
    db.commit()

    return {"detail": "Password reset successfully"}



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

    token_record = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == refresh_in.refresh_token
    ).first()
    if not token_record or token_record.revoked or token_record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or expired")

    user = db.query(models.User).filter(models.User.user_id == token_record.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email verification required")

    token_record.revoked = True
    db.commit()

    access_token = create_access_token(
        data={"sub": str(user.user_id), "student_id": user.student_id},
        expires_delta=timedelta(minutes=60),
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.user_id), "student_id": user.student_id}
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


@router.get("/me", response_model=schemas.UserOut)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=schemas.UserOut)
def update_current_user(
    user_in: schemas.UserAccountUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = user_in.dict(exclude_unset=True)

    if "student_id" in update_data:
        student_id = update_data["student_id"]
        if not validate_student_id(student_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student ID must be 9 digits")
        existing_user = db.query(models.User).filter(models.User.student_id == student_id).first()
        if existing_user and existing_user.user_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student ID already registered")

    if "nickname" in update_data:
        existing_user = db.query(models.User).filter(models.User.nickname == update_data["nickname"]).first()
        if existing_user and existing_user.user_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nickname already taken")

    if update_data.get("password"):
        update_data["password"] = get_password_hash(update_data["password"])

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me")
def delete_current_user(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(models.Friend).filter(
        (models.Friend.user_id == current_user.user_id)
        | (models.Friend.friend_user_id == current_user.user_id)
    ).delete(synchronize_session=False)
    db.query(models.UserQuizConnect).filter(models.UserQuizConnect.user_id == current_user.user_id).delete()
    db.query(models.SchoolFoodFeed).filter(models.SchoolFoodFeed.user_id == current_user.user_id).delete()
    db.query(models.Character).filter(models.Character.user_id == current_user.user_id).delete()
    db.query(models.RefreshToken).filter(models.RefreshToken.user_id == current_user.user_id).delete()
    db.query(models.PasswordResetToken).filter(models.PasswordResetToken.user_id == current_user.user_id).delete()
    db.delete(current_user)
    db.commit()
    return {"detail": "User deleted"}


@router.post("/logout")
def logout(refresh_in: schemas.RefreshRequest, db: Session = Depends(get_db)):
    token_record = db.query(models.RefreshToken).filter(models.RefreshToken.token == refresh_in.refresh_token).first()
    if not token_record or token_record.revoked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")
    token_record.revoked = True
    db.commit()
    return {"detail": "Logged out"}


@router.get("/", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, user_in: schemas.UserUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_in.dict(exclude_unset=True)
    if update_data.get("password"):
        update_data["password"] = get_password_hash(update_data["password"])

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}
