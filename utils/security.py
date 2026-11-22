import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from config.settings import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return await asyncio.to_thread(
        _verify_password, plain_password, hashed_password
    )


def _hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("密码不能超过 72 字节")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hash_password, password)


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    lifetime = expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {**data, "exp": datetime.now(UTC) + lifetime},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
