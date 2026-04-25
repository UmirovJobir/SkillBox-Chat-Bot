from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

# create_async_engine — создаёт async соединение с БД через asyncpg
# settings.database_url = "postgresql+asyncpg://user:pass@host:port/dbname"
engine = create_async_engine(settings.database_url)

# async_sessionmaker — фабрика async сессий
# expire_on_commit=False — не инвалидировать атрибуты объектов после commit().
# В sync ORM это безопасно (объект перезагружается при следующем обращении),
# но в async это вызовет ошибку ленивой загрузки — поэтому отключаем.
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# Base — базовый класс для всех моделей
# Все модели наследуют от него: class User(Base):
class Base(DeclarativeBase):
    pass


async def get_database_session():
    """
    Async Dependency для FastAPI — предоставляет сессию БД для каждого запроса.

    async with AsyncSessionLocal() — сессия закрывается автоматически при выходе
    из контекстного менеджера (даже при исключении). Явный session.close() не нужен.

    Использование в роутере:
        async def my_endpoint(db: AsyncSession = Depends(get_database_session)):
            result = await db.execute(select(User))
    """
    async with AsyncSessionLocal() as session:
        yield session
