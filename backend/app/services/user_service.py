from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import hash_password, verify_password
from ..models.user_model import User
from ..schemas.user_schema import UserRegister


def create_user(database_session: Session, user_data: UserRegister) -> User:
    """
    Создаёт нового пользователя.
    Пароль хешируется ПЕРЕД записью в БД
    """
    hashed = hash_password(user_data.password)
    new_user = User(
        telegram_id=user_data.telegram_id,
        username=user_data.username,
        hashed_password=hashed,  # сохраняем хеш, не сам пароль
    )
    database_session.add(new_user)
    database_session.commit()
    database_session.refresh(new_user)
    return new_user


def find_user_by_telegram_id(database_session: Session, telegram_id: int) -> Optional[User]:
    """
    Ищет пользователя по telegram_id. Возвращает None если не найден.
    """
    stmt = select(User).where(User.telegram_id == telegram_id)
    return database_session.scalars(stmt).first()


def find_user_by_username(database_session: Session, username: str) -> Optional[User]:
    """
    Ищет пользователя по username для проверки уникальности при регистрации.
    """
    stmt = select(User).where(User.username == username)
    return database_session.scalars(stmt).first()


def authenticate_user(
    database_session: Session,
    telegram_id: int,
    plain_password: str,
) -> Optional[User]:
    """
    Проверяет учётные данные пользователя.
    Возвращает User при успехе, None при неверном пароле или отсутствии пользователя.

    Важно: мы не говорим клиенту "пользователь не найден" или "неверный пароль" отдельно.
    Обе ошибки → "Invalid credentials". Это предотвращает перебор существующих пользователей.
    """
    found_user = find_user_by_telegram_id(database_session, telegram_id)
    if found_user is None:
        return None
    if not verify_password(plain_password, found_user.hashed_password):
        return None
    return found_user


def update_user_notification_time(
    database_session: Session,
    user: User,
    notification_time,
) -> User:
    """
    Обновляет время уведомления. notification_time=None → отключить.
    """
    user.notification_time = notification_time
    database_session.commit()
    database_session.refresh(user)
    return user