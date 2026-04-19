from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.auth_router import auth_router
from .routers.habits_router import habits_router
from .routers.users_router import users_router

# FastAPI() — создаёт WSGI приложение
# title, description — отображаются в Swagger документации
application = FastAPI(
    title="Habit Tracker API",
    description="API для Telegram-бота трекинга привычек",
    version="1.0.0",
)

# CORS — разрешает запросы из других источников (нужно если фронтенд на другом домене)
# В нашем случае бот обращается с другого контейнера, поэтому allow_origins=["*"]
application.add_middleware(
    CORSMiddleware,         # type: ignore[arg-type]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры — регистрируем все endpoint'ы
application.include_router(auth_router)    # /auth/register, /auth/login
application.include_router(habits_router)  # /habits и /habits/{id}/*
application.include_router(users_router)   # /users/me и /users/me/notification-time


@application.get("/health", tags=["Health"])
def health_check():
    """
    GET /health — проверка работоспособности.
    Docker и другие сервисы используют это для healthcheck.
    """
    return {"status": "ok"}