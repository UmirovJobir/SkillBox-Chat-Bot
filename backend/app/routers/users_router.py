from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_database_session
from ..models.user_model import User
from ..schemas.user_schema import NotificationTimeUpdate, UserResponse
from ..services.user_service import update_user_notification_time

users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """GET /users/me — профиль текущего пользователя."""
    # current_user уже загружен через get_current_user
    # FastAPI сериализует его через UserResponse (из from_attributes=True)
    return current_user


@users_router.put("/me/notification-time", response_model=UserResponse)
async def set_notification_time(
    time_data: NotificationTimeUpdate,
    current_user: User = Depends(get_current_user),
    database_session: AsyncSession = Depends(get_database_session),
):
    """PUT /users/me/notification-time — задать время уведомления."""
    updated_user = await update_user_notification_time(
        database_session,
        current_user,
        time_data.notification_time,  # может быть None (отключить)
    )
    return updated_user
