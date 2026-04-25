from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import create_access_token
from ..database import get_database_session
from ..schemas.user_schema import Token, UserLogin, UserRegister
from ..services.user_service import (
    authenticate_user,
    create_user,
    find_user_by_telegram_id,
    find_user_by_username,
)

# APIRouter — группирует endpoint'ы
# prefix="/auth" → все URL начинаются с /auth
# tags=["Authentication"] → группировка в Swagger документации
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post(
    "/register",          # URL: POST /auth/register
    response_model=Token, # FastAPI автоматически сериализует ответ через Token schema
    status_code=status.HTTP_201_CREATED,  # 201 Created (не 200 OK)
)
async def register_user(
    user_data: UserRegister,  # FastAPI читает JSON из тела запроса и валидирует
    database_session: AsyncSession = Depends(get_database_session),  # сессия БД
):
    """
    Регистрирует нового пользователя.
    Возвращает JWT токен для немедленного использования.
    """
    # Проверка: уже зарегистрирован с этим Telegram ID?
    existing_by_telegram = await find_user_by_telegram_id(
        database_session, user_data.telegram_id
    )
    if existing_by_telegram:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,  # 409 Conflict
            detail="User with this Telegram ID already exists",
        )

    # Проверка: username занят?
    existing_by_username = await find_user_by_username(
        database_session, user_data.username
    )
    if existing_by_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    new_user = await create_user(database_session, user_data)
    access_token = create_access_token(new_user.id)
    return Token(access_token=access_token)


@auth_router.post("/login", response_model=Token)  # POST /auth/login
async def login_user(
    login_data: UserLogin,
    database_session: AsyncSession = Depends(get_database_session),
):
    """Аутентифицирует пользователя. Возвращает JWT токен."""
    existing_user = await find_user_by_telegram_id(database_session, login_data.telegram_id)
    if existing_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    authenticated_user = await authenticate_user(
        database_session,
        login_data.telegram_id,
        login_data.password,
    )
    if authenticated_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    access_token = create_access_token(authenticated_user.id)
    return Token(access_token=access_token)
