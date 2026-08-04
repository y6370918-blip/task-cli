from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

created_at: Mapped[datetime] = mapped_column(
    DateTime, nullable=False, default=datetime.now
)

updated_at: Mapped[datetime] = mapped_column(
    DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
)
