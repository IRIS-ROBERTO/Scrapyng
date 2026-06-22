from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

import enum


class JobType(str, enum.Enum):
    instant = "instant"
    scheduled = "scheduled"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    paused = "paused"


class ScrapingJob(Base):
    __tablename__ = "scraping_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    job_type: Mapped[str] = mapped_column(
        Enum(JobType, name="job_type_enum"), default=JobType.instant, nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(JobStatus, name="job_status_enum"),
        default=JobStatus.pending,
        nullable=False,
        index=True,
    )
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="scraping_jobs")  # noqa: F821
    runs: Mapped[list["ScrapingRun"]] = relationship(  # noqa: F821
        "ScrapingRun", back_populates="job", cascade="all, delete-orphan"
    )
    schedule: Mapped["ScrapingSchedule | None"] = relationship(  # noqa: F821
        "ScrapingSchedule", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ScrapingJob id={self.id} name={self.name} status={self.status}>"
