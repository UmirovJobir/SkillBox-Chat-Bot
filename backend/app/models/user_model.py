from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Time
from sqlalchemy.orm import relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    notification_time = Column(Time, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    habits = relationship(
        "Habit",
        back_populates="user",
        cascade="all, delete-orphan",
    )