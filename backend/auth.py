import os
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from config import get_int_env, is_production_env, load_env_file


load_env_file()


def _get_expire_minutes() -> int:
    expire_minutes = get_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    return expire_minutes if expire_minutes > 0 else 60


def _get_secret_key() -> str:
    configured_secret = os.getenv("APP_SECRET_KEY") or os.getenv("SECRET_KEY")
    if configured_secret:
        return configured_secret.strip()

    if is_production_env():
        raise RuntimeError(
            "APP_SECRET_KEY or SECRET_KEY must be set when APP_ENV=production."
        )

    return secrets.token_urlsafe(32)


SECRET_KEY = _get_secret_key()
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = _get_expire_minutes()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
