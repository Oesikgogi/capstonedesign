import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "boo_app_change_this_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30
EMAIL_VERIFICATION_EXPIRE_HOURS = 24
PASSWORD_RESET_EXPIRE_HOURS = 24


def get_password_hash(password: str) -> str:
    salt = SECRET_KEY.encode()
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000).hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire, "jti": secrets.token_urlsafe(16)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire, "type": "refresh", "jti": secrets.token_urlsafe(16)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_password_reset_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    return token


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise
