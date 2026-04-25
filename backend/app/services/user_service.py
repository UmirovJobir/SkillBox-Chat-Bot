from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import hash_password, verify_password
from ..models.user_model import User
from ..schemas.user_schema import UserRegister


async def create_user(database_session: AsyncSession, user_data: UserRegister) -> User:
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
    await database_session.commit()
    await database_session.refresh(new_user)
    return new_user


async def find_user_by_telegram_id(
    database_session: AsyncSession, telegram_id: int
) -> Optional[User]:
    """
    Ищет пользователя по telegram_id. Возвращает None если не найден.
    """
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await database_session.execute(stmt)
    return result.scalars().first()


async def find_user_by_username(
    database_session: AsyncSession, username: str
) -> Optional[User]:
    """
    Ищет пользователя по username для проверки уникальности при регистрации.
    """
    stmt = select(User).where(User.username == username)
    result = await database_session.execute(stmt)
    return result.scalars().first()


async def authenticate_user(
    database_session: AsyncSession,
    telegram_id: int,
    plain_password: str,
) -> Optional[User]:
    """
    Проверяет учётные данные пользователя.
    Возвращает User при успехе, None при неверном пароле или отсутствии пользователя.

    Важно: мы не говорим клиенту "пользователь не найден" или "неверный пароль" отдельно.
    Обе ошибки → "Invalid credentials". Это предотвращает перебор существующих пользователей.
    """
    found_user = await find_user_by_telegram_id(database_session, telegram_id)
    if found_user is None:
        return None
    if not verify_password(plain_password, found_user.hashed_password):
        return None
    return found_user


async def update_user_notification_time(
    database_session: AsyncSession,
    user: User,
    notification_time,
) -> User:
    """
    Обновляет время уведомления. notification_time=None → отключить.
    """
    user.notification_time = notification_time
    await database_session.commit()
    await database_session.refresh(user)
    return user
