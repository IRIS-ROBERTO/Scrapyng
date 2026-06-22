from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
import enum


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class ScrapingRun(Base):
    __tablename__ = "scraping_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[str] = mapped_column(
        Enum(RunStatus, name="run_status_enum"),
        default=RunStatus.pending,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    items_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=0)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Foreign keys
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scraping_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    job: Mapped["ScrapingJob"] = relationship("ScrapingJob", back_populates="runs")  # noqa: F821
    results: Mapped[list["ScrapingResult"]] = relationship(  # noqa: F821
        "ScrapingResult", back_populates="run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ScrapingRun id={self.id} job_id={self.job_id} status={self.status}>"
