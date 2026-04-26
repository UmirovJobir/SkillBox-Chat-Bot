# SkillBox Habit Tracker Bot

Telegram-бот для трекинга ежедневных привычек. Помогает создавать привычки, отмечать выполнение и получать напоминания в заданное время.

## Демонстрация

> **Видео-демонстрация работы сервиса:** [ссылка на видео](https://drive.google.com/file/d/1Kd69u6vEXm9-qlVFINjmMQ_dJQPcwEq2/view?usp=sharing)

---

## Отчёт по проекту

### Что сделано и готовность по ТЗ

Сервис реализован полностью. Весь заявленный функционал работает:

- **Регистрация и авторизация** — через Telegram ID + пароль. JWT-токен выдаётся при регистрации и при входе.
- **Привычки** — создание с названием, описанием и целью (по умолчанию 21 день), просмотр списка, редактирование, удаление.
- **Выполнение** — ежедневная отметка с прогресс-баром (`total_completions / target_completions`). Повторная отметка в тот же день отклоняется.
- **Автозавершение** — при достижении цели привычка автоматически помечается неактивной (`is_active = False`).
- **Уведомления** — APScheduler проверяет каждую минуту; если текущее время совпадает с `notification_time` пользователя — бот отправляет напоминание со списком невыполненных привычек.
- **Docker** — три контейнера (postgres, backend, bot); миграции применяются автоматически при старте.
- **Async backend** — FastAPI + AsyncSQLAlchemy 2.0 + asyncpg (полностью неблокирующий стек).

### Аутентификация в Swagger

Swagger UI доступен по адресу `http://localhost:8000/docs`.

1. Выполните `POST /auth/register` или `POST /auth/login` — в ответе получите `access_token`.
2. Нажмите кнопку **Authorize** (замок в правом верхнем углу).
3. В поле введите: `Bearer <ваш_токен>` и нажмите **Authorize**.

После этого все защищённые эндпоинты (`/habits`, `/users/me` и др.) будут автоматически отправлять заголовок `Authorization: Bearer <токен>`.

### Аутентификация пользователя из бота

При нажатии `/start` бот предлагает **Войти** или **Зарегистрироваться**.

**Регистрация:** бот последовательно запрашивает имя пользователя и пароль, затем отправляет `POST /auth/register` с `{telegram_id, username, password}` на backend. При успехе получает JWT-токен и сохраняет его в памяти.

**Вход:** бот запрашивает пароль, затем отправляет `POST /auth/login` с `{telegram_id, password}`. Backend проверяет пароль через bcrypt и возвращает JWT-токен.

Все последующие запросы к backend (получение привычек, создание, отметка) бот делает с заголовком `Authorization: Bearer <token>`.

### Хранение токенов в боте

Токены хранятся в оперативной памяти — словарь `user_tokens: dict[int, str]` в файле `bot/handlers/auth_handler.py`, где ключ — `telegram_id` пользователя.

```python
# bot/handlers/auth_handler.py
user_tokens: dict[int, str] = {}
```

Этот же словарь передаётся в `scheduler.py` по ссылке — планировщик использует его при отправке уведомлений.

**Важно:** персистентность не реализована. При перезапуске бота все токены очищаются — пользователям необходимо войти заново.

### Обновление токенов после истечения

Автоматическое обновление токенов (refresh token) **не реализовано**. Токен живёт `ACCESS_TOKEN_EXPIRE_MINUTES` минут (по умолчанию 10080 = 7 дней).

Когда токен истекает, backend возвращает `401 Unauthorized`. Бот перехватывает этот статус в `api_client.py` и предлагает пользователю войти заново через `/start`.

---

## Стек

| Слой | Технологии |
|---|---|
| Бот | Python 3.11, pyTelegramBotAPI, APScheduler |
| Backend | FastAPI (async), AsyncSQLAlchemy 2.0, Alembic, JWT (PyJWT), pwdlib |
| Драйвер БД | asyncpg (асинхронный PostgreSQL драйвер) |
| База данных | PostgreSQL 15 |
| Инфраструктура | Docker, Docker Compose |

## Архитектура

```
┌─────────────┐     HTTP     ┌──────────────────┐   asyncpg    ┌──────────────┐
│ Telegram Bot│ ──────────── │  FastAPI (async) │ ──────────── │  PostgreSQL  │
│  (bot/)     │              │  (backend/)      │              │              │
└─────────────┘              └──────────────────┘              └──────────────┘
```

Три независимых Docker-контейнера, общаются по внутренней сети Docker.
Backend полностью асинхронный: все endpoints и обращения к БД используют `async/await`.

## Возможности

- Регистрация и авторизация через Telegram ID
- Создание привычек с названием, описанием и целью (по умолчанию 21 день)
- Отметка выполнения с прогресс-баром
- Редактирование и удаление привычек
- Уведомления в заданное время (по часовому поясу из `.env`)
- Автоматическое завершение привычки при достижении цели

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/UmirovJobir/SkillBox-Chat-Bot.git
cd SkillBox-Chat-Bot
```

### 2. Создать `.env`

Скопируйте пример и заполните своими значениями:

```bash
cp .env.example .env
```

Обязательные переменные:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=habit_tracker_db

SECRET_KEY=your-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

TELEGRAM_BOT_TOKEN=your_token_from_botfather

HABIT_TARGET_DAYS=21
TIMEZONE=Asia/Tashkent
```

> Получить токен бота: [@BotFather](https://t.me/BotFather) → `/newbot`

### 3. Запустить

```bash
docker-compose up --build
```

При первом запуске Docker автоматически:
1. Поднимет PostgreSQL
2. Применит миграции (`alembic upgrade head`)
3. Запустит FastAPI на порту `8000`
4. Запустит Telegram-бот

### 4. Проверить

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Бот: найдите его в Telegram и отправьте `/start`

## Локальная разработка (без Docker)

### Backend

Требуется локальный PostgreSQL на порту `5433` с `postgresql+asyncpg://` URL.

```bash
cd backend
poetry install
# DATABASE_URL должен быть установлен в окружении:
# export DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5433/habit_tracker_db
alembic upgrade head
uvicorn app.main:application --reload --port 8000
```

### Bot

```bash
cd bot
poetry install
# BACKEND_URL=http://localhost:8000 и TELEGRAM_BOT_TOKEN должны быть в окружении
python main.py
```

## Структура проекта

```
SkillBox-Chat-Bot/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI приложение (async)
│   │   ├── auth.py           # JWT и хеширование паролей, async get_current_user
│   │   ├── config.py         # Настройки из .env
│   │   ├── database.py       # create_async_engine, AsyncSession, get_database_session
│   │   ├── models/           # User, Habit, HabitLog
│   │   ├── routers/          # async endpoints: auth, habits, users
│   │   ├── schemas/          # Pydantic схемы
│   │   └── services/         # Async бизнес-логика (await db.execute)
│   ├── alembic/              # Миграции БД (async engine через run_sync)
│   └── Dockerfile
├── bot/
│   ├── main.py               # Точка входа
│   ├── scheduler.py          # APScheduler уведомления
│   ├── handlers/             # auth, habits, start
│   ├── keyboards/            # Inline-клавиатуры
│   ├── services/             # HTTP-клиент к backend
│   └── Dockerfile
├── docker-compose.yml
└── .env
```

## API endpoints

| Метод | URL | Описание |
|---|---|---|
| POST | `/auth/register` | Регистрация |
| POST | `/auth/login` | Вход, возвращает JWT |
| GET | `/habits` | Список привычек |
| POST | `/habits` | Создать привычку |
| PUT | `/habits/{id}` | Обновить привычку |
| DELETE | `/habits/{id}` | Удалить привычку |
| POST | `/habits/{id}/complete` | Отметить выполненной |
| PUT | `/users/me/notification-time` | Настроить уведомление |
| GET | `/users/me` | Профиль пользователя |

## Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `POSTGRES_USER` | Пользователь БД | `postgres` |
| `POSTGRES_PASSWORD` | Пароль БД | `secret` |
| `POSTGRES_DB` | Имя БД | `habit_tracker_db` |
| `SECRET_KEY` | Секрет для подписи JWT | `random-32-char-string` |
| `ALGORITHM` | Алгоритм JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни токена | `10080` (7 дней) |
| `TELEGRAM_BOT_TOKEN` | Токен от @BotFather | `123456:ABC-DEF...` |
| `HABIT_TARGET_DAYS` | Дней для выработки привычки | `21` |
| `TIMEZONE` | Часовой пояс уведомлений | `Asia/Tashkent` |