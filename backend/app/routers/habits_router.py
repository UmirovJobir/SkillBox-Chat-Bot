from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_database_session
from ..models.user_model import User
from ..schemas.habit_schema import HabitCreate, HabitResponse, HabitUpdate
from ..services.habit_service import (
    check_habit_completed_today,
    create_habit,
    delete_habit,
    get_active_habits_for_user,
    get_habit_by_id,
    mark_habit_completed_today,
    update_habit,
)

habits_router = APIRouter(prefix="/habits", tags=["Habits"])


async def build_habit_response(habit, database_session: AsyncSession) -> HabitResponse:
    """
    Вспомогательная функция: конвертирует SQLAlchemy Habit в Pydantic HabitResponse.
    Добавляет вычисляемое поле is_completed_today (его нет в таблице habits).
    """
    is_completed = await check_habit_completed_today(database_session, habit.id)
    return HabitResponse(
        id=habit.id,
        title=habit.title,
        description=habit.description,
        target_completions=habit.target_completions,
        total_completions=habit.total_completions,
        is_active=habit.is_active,
        is_completed_today=is_completed,
        created_at=habit.created_at,
    )


@habits_router.get("", response_model=List[HabitResponse])
async def get_all_habits(
    # Depends(get_current_user) → JWT токен проверяется автоматически
    # Если токена нет или он неверный → 401 Unauthorized (до вызова функции)
    current_user: User = Depends(get_current_user),
    database_session: AsyncSession = Depends(get_database_session),
):
    """GET /habits — список всех активных привычек пользователя."""
    active_habits = await get_active_habits_for_user(database_session, current_user.id)
    # Для каждой привычки добавляем is_completed_today
    return [await build_habit_response(habit, database_session) for habit in active_habits]


@habits_router.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
async def create_new_habit(
    habit_data: HabitCreate,
    current_user: User = Depends(get_current_user),
    database_session: AsyncSession = Depends(get_database_session),
):
    """POST /habits — создать новую привычку."""
    new_habit = await create_habit(database_session, current_user.id, habit_data)
    return await build_habit_response(new_habit, database_session)


@habits_router.put("/{habit_id}", response_model=HabitResponse)
async def update_existing_habit(
    habit_id: int,  # FastAPI берёт из URL: PUT /habits/5 → habit_id=5
    update_data: HabitUpdate,
    current_user: User = Depends(get_current_user),
    database_session: AsyncSession = Depends(get_database_session),
):
    """PUT /habits/{habit_id} — обновить привычку."""
    found_habit = await get_habit_by_id(database_session, habit_id, current_user.id)
    if found_habit is None:
        # 404 если не нашли (или это чужая привычка — тоже 404, не 403)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    updated_habit = await update_habit(database_session, found_habit, update_data)
    return await build_habit_response(updated_habit, database_session)


@habits_router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_habit(
    habit_id: int,
    current_user: User = Depends(get_current_user),
    database_session: AsyncSession = Depends(get_database_session),
):
    """DELETE /habits/{habit_id} — удалить привычку. 204 No Content = без тела ответа."""
    found_habit = await get_habit_by_id(database_session, habit_id, current_user.id)
    if found_habit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    await delete_habit(database_session, found_habit)
    # FastAPI автоматически вернёт 204 без тела ответа


@habits_router.post("/{habit_id}/complete", response_model=HabitResponse)
async def complete_habit_today(
    habit_id: int,
    current_user: User = Depends(get_current_user),
    database_session: AsyncSession = Depends(get_database_session),
):
    """POST /habits/{habit_id}/complete — отметить привычку выполненной сегодня."""
    found_habit = await get_habit_by_id(database_session, habit_id, current_user.id)
    if found_habit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    await mark_habit_completed_today(database_session, found_habit)
    # После mark_habit_completed_today объект found_habit обновился в БД
    # refresh() — синхронизируем Python объект с актуальным состоянием в БД
    await database_session.refresh(found_habit)
    return await build_habit_response(found_habit, database_session)
