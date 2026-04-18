from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

# create_engine — создаёт соединение с БД
# settings.database_url = "postgresql://user:pass@host:port/dbname"
engine = create_engine(settings.database_url)

# sessionmaker — фабрика сессий
# autocommit=False — мы сами вызываем session.commit() когда готовы
# autoflush=False  — не отправлять SQL до commit()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base — базовый класс для всех моделей
# Все модели наследуют от него: class User(Base):
Base = declarative_base()


def get_database_session():
    """
    Dependency для FastAPI — предоставляет сессию БД для каждого запроса.

    FastAPI вызывает эту функцию при каждом HTTP запросе.
    yield — это генератор: код ДО yield выполняется перед запросом,
    код ПОСЛЕ yield выполняется после (закрывает сессию).

    Использование в роутере:
        def my_endpoint(db: Session = Depends(get_database_session)):
            users = db.query(User).all()
    """
    session = SessionLocal()
    try:
        yield session        # передаём сессию в роутер
    finally:
        session.close()      # закрываем сессию после запроса (даже при ошибке)