from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_database_session
from .models.user_model import User

# PasswordHash — главный объект pwdlib для хеширования и проверки паролей.
# Принимает кортеж хешеров; первый считается активным (используется для hash()).
# BcryptHasher() — алгоритм bcrypt: добавляет случайную соль, необратим,
# устойчив к брутфорсу за счёт настраиваемой вычислительной стоимости (rounds).
# Пример: password_hash.hash("secret") → "$2b$12$abc...xyz"
#          password_hash.verify("secret", "$2b$12$abc...xyz") → True
password_hash = PasswordHash((BcryptHasher(),))

# HTTPBearer — схема авторизации через заголовок "Authorization: Bearer <token>"
# FastAPI автоматически извлекает токен из заголовка
bearer_scheme = HTTPBearer()


def hash_password(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    """
    Создаёт JWT токен для пользователя.

    JWT структура: header.payload.signature
    payload = {"sub": "42", "exp": 1714000000}
    "sub" (subject) = ID пользователя в нашей БД
    "exp" (expiration) = время истечения токена (Unix timestamp)

    jwt.encode() подписывает payload секретным ключом.
    Если изменить любой символ в токене — подпись не совпадёт → 401 Unauthorized.
    """
    payload = {
        "sub": str(user_id),  # строка, не число (стандарт JWT)
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    database_session: Session = Depends(get_database_session),
) -> User:
    """
    FastAPI Dependency: извлекает текущего пользователя из JWT токена.

    Используется в роутерах через:
        current_user: User = Depends(get_current_user)

    FastAPI автоматически:
    1. Читает заголовок "Authorization: Bearer eyJhbGc..."
    2. Передаёт токен в credentials.credentials
    3. Вызывает эту функцию перед вызовом endpoint функции
    """
    token = credentials.credentials  # сам JWT токен (без "Bearer ")
    try:
        # jwt.decode() проверяет подпись и срок действия токена
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        # "sub" — ID пользователя, сохранённый при создании токена
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        user_id = int(user_id_str)
    except jwt.ExpiredSignatureError:
        # Токен истёк (прошло больше access_token_expire_minutes минут)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        # Токен подделан или повреждён
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Находим пользователя в БД по ID из токена
    found_user = database_session.scalars(select(User).where(User.id == user_id)).first()
    if found_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return found_user  # FastAPI передаст этот объект в endpoint функцию