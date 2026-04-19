from datetime import time
from typing import Optional

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    """Данные для регистрации. Бот отправляет этот JSON на POST /auth/register."""
    telegram_id: int
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    """Данные для входа. Бот отправляет на POST /auth/login."""
    telegram_id: int
    password: str


class UserResponse(BaseModel):
    """Что возвращаем клиенту."""
    id: int
    telegram_id: int
    username: str
    notification_time: Optional[time] = None  # None если не настроено

    class Config:
        # from_attributes=True — позволяет создавать из SQLAlchemy объекта:
        # user = db.query(User).first()
        # UserResponse.model_validate(user)  ← без этого не работает
        from_attributes = True


class Token(BaseModel):
    """Ответ после успешного входа/регистрации."""
    access_token: str
    token_type: str = "bearer"


class NotificationTimeUpdate(BaseModel):
    """Для обновления времени уведомления. None = отключить."""
    notification_time: Optional[time] = None