from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Каждое поле здесь — это переменная из .env файла
    # pydantic-settings автоматически читает .env и заполняет поля
    database_url: str = "postgresql://habit_user:habit_password@localhost:5432/habit_tracker_db"
    secret_key: str = "change-this-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 дней
    habit_target_days: int = 21

    class Config:
        env_file = ".env"  # читать из этого файла


# Создаём один экземпляр и используем везде
# from app.config import settings
settings = Settings()