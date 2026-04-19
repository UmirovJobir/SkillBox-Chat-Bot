import os

from dotenv import load_dotenv

# load_dotenv() читает файл .env и добавляет переменные в os.environ
# В Docker они уже есть в os.environ (через environment: в docker-compose.yml)
# load_dotenv() тогда ничего не перезаписывает — это безопасно
load_dotenv()

# os.getenv("VAR", "default") — читает переменную или возвращает default
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
HABIT_TARGET_DAYS: int = int(os.getenv("HABIT_TARGET_DAYS", "21"))