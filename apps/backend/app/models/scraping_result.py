from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScrapingResult(Base):
    __tablename__ = "scraping_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    structured_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Foreign keys
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scraping_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    run: Mapped["ScrapingRun"] = relationship("ScrapingRun", back_populates="results")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ScrapingResult id={self.id} run_id={self.run_id} score={self.quality_score}>"
