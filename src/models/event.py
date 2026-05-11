"""TelemetryEvent SQLAlchemy model."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class TelemetryEvent(Base, UUIDMixin, TimestampMixin):
    """
    Telemetry event model representing IoT device measurements.

    Idempotency is guaranteed via unique constraint on
    (device_id, timestamp, metric).
    """

    __tablename__ = "telemetry_events"

    device_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    metric: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    value: Mapped[float] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    __table_args__ = (
        # Unique constraint for idempotency - critical for no-duplicate inserts
        UniqueConstraint(
            "device_id", "timestamp", "metric", name="uq_events_device_timestamp_metric"
        ),
        # Index for aggregation queries: device_id + timestamp (descending)
        Index(
            "idx_events_device_timestamp",
            "device_id",
            timestamp.desc(),
        ),
        # Index for metric-specific queries
        Index(
            "idx_events_device_metric",
            "device_id",
            "metric",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TelemetryEvent(device_id={self.device_id}, "
            f"timestamp={self.timestamp}, metric={self.metric}, value={self.value})>"
        )
