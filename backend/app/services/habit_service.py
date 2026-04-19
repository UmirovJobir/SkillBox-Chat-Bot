from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.habit_model import Habit, HabitLog
from ..schemas.habit_schema import HabitCreate, HabitUpdate


def create_habit(
    database_session: Session,
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
    database_session.commit()
    database_session.refresh(new_habit)
    return new_habit


def get_active_habits_for_user(
    database_session: Session,
    user_id: int,
) -> List[Habit]:
    """
    Возвращает все АКТИВНЫЕ привычки пользователя.
    is_active=False → привычка выработана, не показывать.
    """
    stmt = select(Habit).where(Habit.user_id == user_id, Habit.is_active == True)
    return list(database_session.scalars(stmt).all())


def get_habit_by_id(
    database_session: Session,
    habit_id: int,
    user_id: int,
) -> Optional[Habit]:
    """
    Ищет привычку по ID.
    ВАЖНО: фильтруем по user_id — пользователь не должен видеть чужие привычки!
    """
    stmt = select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
    return database_session.scalars(stmt).first()


def update_habit(
    database_session: Session,
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
    database_session.commit()
    database_session.refresh(habit)
    return habit


def delete_habit(database_session: Session, habit: Habit) -> None:
    """Удаляет привычку. HabitLog удаляются автоматически (cascade в модели)."""
    database_session.delete(habit)
    database_session.commit()


def mark_habit_completed_today(
    database_session: Session,
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
    existing_log: HabitLog | None = database_session.scalars(stmt).first()

    if existing_log:
        if not existing_log.is_completed:
            # Запись есть, но ещё не выполнена — обновляем
            existing_log.is_completed = True
            habit.total_completions += 1
            if habit.total_completions >= habit.target_completions:
                habit.is_active = False  # привычка выработана!
            database_session.commit()
            database_session.refresh(existing_log)
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
    database_session.commit()
    database_session.refresh(new_log)
    return new_log


def check_habit_completed_today(
    database_session: Session,
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
    log = database_session.scalars(stmt).first()
    return log is not None  # True если нашли запись, False если нет