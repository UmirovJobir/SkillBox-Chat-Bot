from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HabitCreate(BaseModel):
    """Данные для создания привычки. Бот отправляет на POST /habits."""
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    # ge=1 → greater or equal 1 (минимум 1)
    # le=365 → less or equal 365 (максимум 365)
    target_completions: int = Field(default=21, ge=1, le=365)


class HabitUpdate(BaseModel):
    """
    Данные для обновления. Все поля Optional — можно передать только то, что меняем.
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    target_completions: Optional[int] = Field(None, ge=1, le=365)


class HabitResponse(BaseModel):
    """Что возвращаем клиенту для каждой привычки."""
    id: int
    title: str
    description: Optional[str] = None
    target_completions: int
    total_completions: int
    is_active: bool
    # is_completed_today — вычисляемое поле (нет в таблице habits!)
    # Вычисляется в роутере: есть ли HabitLog за сегодня?
    is_completed_today: bool = False
    created_at: datetime

    class Config:
        from_attributes = True