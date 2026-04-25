
import logging
from datetime import datetime
from typing import Dict

import telebot
from apscheduler.schedulers.background import BackgroundScheduler

from services.api_client import api_client

logger = logging.getLogger(__name__)


def send_habit_reminders(
    bot_instance: telebot.TeleBot,
    user_tokens: Dict[int, str],
) -> None:
    """
    Проверяет всех авторизованных пользователей и отправляет напоминания.
    Вызывается планировщиком каждую минуту.

    Параметры:
        bot_instance — экземпляр бота (для отправки сообщений)
        user_tokens — словарь {telegram_id: jwt_token} из auth_handler.py
                         Это та же dict что используют хендлеры — общая ссылка!
    """
    # Текущее время в формате "HH:MM" — именно так хранит notification_time в БД
    current_time = datetime.now().strftime("%H:%M")

    # list(user_tokens.items()) — создаём копию списка пар (id, token)
    # Копия нужна потому что внутри цикла мы можем изменять user_tokens
    # (удалять просроченные токены), а изменение dict во время итерации → ошибка
    for telegram_id, access_token in list(user_tokens.items()):
        try:
            # Запрашиваем профиль пользователя чтобы узнать его notification_time
            user_result = api_client.get_current_user(access_token)

            if user_result["status_code"] != 200:
                # Токен истёк или недействителен — удаляем пользователя
                # Он должен войти снова через /start
                user_tokens.pop(telegram_id, None)
                logger.info(f"Токен пользователя {telegram_id} устарел, удалён.")
                continue  # переходим к следующему пользователю

            user_data = user_result["data"]
            user_notification_time = user_data.get("notification_time")

            # Если пользователь не настроил уведомления — пропускаем
            if user_notification_time is None:
                continue

            # notification_time из API приходит как "09:00:00" (с секундами)
            # Берём только первые 5 символов: "09:00"
            notification_time_str = str(user_notification_time)[:5]

            # Проверяем: совпадает ли время уведомления с текущим?
            if notification_time_str != current_time:
                continue  # ещё не время

            # ── Время совпало → отправляем напоминание ──────────────────────

            habits_result = api_client.get_all_habits(access_token)
            if habits_result["status_code"] != 200:
                continue

            active_habits = habits_result["data"]
            if not active_habits:
                continue  # нет привычек — нечего напоминать

            # Фильтруем только невыполненные за сегодня
            pending_habits = [
                habit for habit in active_habits
                if not habit.get("is_completed_today")
            ]

            if not pending_habits:
                # Все привычки уже выполнены — поздравляем!
                bot_instance.send_message(
                    telegram_id,
                    "🎉 Отличная работа! Все привычки на сегодня выполнены!",
                )
                continue

            # Формируем текст напоминания
            reminder_lines = [
                f"⏰ Напоминание о привычках!\n"
                f"Невыполнено: {len(pending_habits)} из {len(active_habits)}\n"
            ]
            for habit in pending_habits:
                progress = f"{habit['total_completions']}/{habit['target_completions']}"
                reminder_lines.append(f"⭕ {habit['title']} ({progress} дней)")

            reminder_lines.append("\nНажмите '📋 Мои привычки' чтобы отметить.")
            reminder_text = "\n".join(reminder_lines)

            # Отправляем сообщение пользователю
            bot_instance.send_message(telegram_id, reminder_text)
            logger.info(f"Напоминание отправлено пользователю {telegram_id}")

        except Exception as error:
            # Ловим любую ошибку чтобы не останавливать планировщик
            # Если один пользователь дал ошибку — остальные всё равно получат напоминание
            logger.error(
                f"Ошибка при напоминании для {telegram_id}: {error}"
            )


def setup_scheduler(
    bot_instance: telebot.TeleBot,
    user_tokens: Dict[int, str],
) -> BackgroundScheduler:
    """
    Создаёт и запускает APScheduler в фоновом потоке.

    BackgroundScheduler — работает в отдельном потоке, не блокирует бота.
    timezone="UTC" — важно: совпадает с временем в БД (created_at в UTC).

    Возвращаем scheduler чтобы main.py мог вызвать scheduler.shutdown()
    при остановке бота.
    """
    scheduler = BackgroundScheduler(timezone="UTC")

    # add_job — добавляем задачу в планировщик
    scheduler.add_job(
        send_habit_reminders,       # функция для запуска
        trigger="cron",             # тип триггера: по расписанию
        minute="*",                 # каждую минуту (аналог: "* * * * *" в crontab)
        args=[bot_instance, user_tokens],  # аргументы функции
        id="send_habit_reminders",  # уникальный ID задачи
        replace_existing=True,      # если задача с таким ID уже есть — заменить
    )

    scheduler.start()
    logger.info("Планировщик уведомлений запущен (каждую минуту).")
    return scheduler