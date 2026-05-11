"""Add composite index for aggregation queries.

Revision ID: 002
Revises: 001
Create Date: 2026-05-10
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite index for aggregation queries.

    This index optimizes queries filtering by device_id + metric + timestamp
    which is the common pattern for aggregation endpoints.
    """
    # Composite index covering all three columns used in WHERE clauses
    op.create_index(
        "idx_aggregation_cover",
        "telemetry_events",
        ["device_id", "metric", "timestamp"],
    )


def downgrade() -> None:
    """Drop aggregation cover index."""
    op.drop_index("idx_aggregation_cover", table_name="telemetry_events")
