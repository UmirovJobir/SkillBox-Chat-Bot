from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.habit_model import Habit, HabitLog
from ..schemas.habit_schema import HabitCreate, HabitUpdate


async def create_habit(
    database_session: AsyncSession,
    user_id: int,
    habit_data: HabitCreate,
) -> Habit:
    """Создаёт новую привычку для пользователя."""
    new_habit = Habit(
        user_id=user_id,
        title=habit_data.title,
        description=habit_data.description,
        target_completions=habit_data.target_completions,
        # total_completions=0, is_active=True — из default в модели
    )
    database_session.add(new_habit)
    await database_session.commit()
    await database_session.refresh(new_habit)
    return new_habit


async def get_active_habits_for_user(
    database_session: AsyncSession,
    user_id: int,
) -> List[Habit]:
    """
    Возвращает все АКТИВНЫЕ привычки пользователя.
    is_active=False → привычка выработана, не показывать.
    """
    stmt = select(Habit).where(Habit.user_id == user_id, Habit.is_active == True)
    result = await database_session.execute(stmt)
    return list(result.scalars().all())


async def get_habit_by_id(
    database_session: AsyncSession,
    habit_id: int,
    user_id: int,
) -> Optional[Habit]:
    """
    Ищет привычку по ID.
    ВАЖНО: фильтруем по user_id — пользователь не должен видеть чужие привычки!
    """
    stmt = select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
    result = await database_session.execute(stmt)
    return result.scalars().first()


async def update_habit(
    database_session: AsyncSession,
    habit: Habit,
    update_data: HabitUpdate,
) -> Habit:
    """
    Обновляет только переданные поля.
    Если title=None → не трогаем title. Это позволяет обновлять по одному полю.
    """
    if update_data.title is not None:
        habit.title = update_data.title
    if update_data.description is not None:
        habit.description = update_data.description
    if update_data.target_completions is not None:
        habit.target_completions = update_data.target_completions
    await database_session.commit()
    await database_session.refresh(habit)
    return habit


async def delete_habit(database_session: AsyncSession, habit: Habit) -> None:
    """Удаляет привычку. HabitLog удаляются автоматически (cascade в модели)."""
    await database_session.delete(habit)
    await database_session.commit()


async def mark_habit_completed_today(
    database_session: AsyncSession,
    habit: Habit,
) -> HabitLog:
    """
    Отмечает привычку выполненной за сегодня.

    Логика:
    1. Проверить: есть ли уже запись за сегодня?
       - Есть и is_completed=True → ничего не делаем (уже отмечено)
       - Есть и is_completed=False → меняем на True, увеличиваем счётчик
       - Нет → создаём новую запись, увеличиваем счётчик
    2. Если total_completions >= target_completions → деактивируем привычку
    """
    today = date.today()

    # Ищем существующую запись за сегодня
    stmt = select(HabitLog).where(HabitLog.habit_id == habit.id, HabitLog.log_date == today)
    result = await database_session.execute(stmt)
    existing_log: HabitLog | None = result.scalars().first()

    if existing_log:
        if not existing_log.is_completed:
            # Запись есть, но ещё не выполнена — обновляем
            existing_log.is_completed = True
            habit.total_completions += 1
            if habit.total_completions >= habit.target_completions:
                habit.is_active = False  # привычка выработана!
            await database_session.commit()
            await database_session.refresh(existing_log)
        return existing_log  # уже было выполнено — возвращаем как есть

    # Записи за сегодня нет — создаём новую
    new_log: HabitLog = HabitLog(
        habit_id=habit.id,
        log_date=today,
        is_completed=True,
    )
    database_session.add(new_log)
    habit.total_completions += 1
    if habit.total_completions >= habit.target_completions:
        habit.is_active = False  # цель достигнута — 21 день выполнено!
    await database_session.commit()
    await database_session.refresh(new_log)
    return new_log


async def check_habit_completed_today(
    database_session: AsyncSession,
    habit_id: int,
) -> bool:
    """
    Проверяет: отмечена ли привычка выполненной сегодня?
    Используется для формирования is_completed_today в ответе.
    """
    today = date.today()
    stmt = select(HabitLog).where(
        HabitLog.habit_id == habit_id,
        HabitLog.log_date == today,
        HabitLog.is_completed == True,
    )
    result = await database_session.execute(stmt)
    return result.scalars().first() is not None
