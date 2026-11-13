from datetime import datetime

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ApiConfig(Base):
    __tablename__ = "api_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    url: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(String(10), default="GET")
    headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeout: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    schedules: Mapped[list["ApiSchedule"]] = relationship(
        back_populates="api", cascade="all, delete-orphan", order_by="ApiSchedule.time_of_day"
    )


class ApiSchedule(Base):
    __tablename__ = "api_schedules"
    __table_args__ = (UniqueConstraint("api_id", "time_of_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    api_id: Mapped[int] = mapped_column(ForeignKey("api_configs.id", ondelete="CASCADE"))
    time_of_day: Mapped[str] = mapped_column(String(5))  # format HH:MM

    api: Mapped[ApiConfig] = relationship(back_populates="schedules")


class ApiExecutionLog(Base):
    __tablename__ = "api_execution_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_configs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    api_name: Mapped[str] = mapped_column(String(150))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str] = mapped_column(String(15), default="scheduler")  # scheduler / manual
