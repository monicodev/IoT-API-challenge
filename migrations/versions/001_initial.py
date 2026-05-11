"""Initial migration - Create telemetry_events table.

Revision ID: 001
Revises:
Create Date: 2026-01-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create telemetry_events table with indexes."""
    op.create_table(
        'telemetry_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', sa.String(255), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metric', sa.String(100), nullable=False),
        sa.Column('value', sa.Numeric(20, 6), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Unique constraint for idempotency
    op.create_unique_constraint(
        'uq_events_device_timestamp_metric',
        'telemetry_events',
        ['device_id', 'timestamp', 'metric']
    )

    # Indexes for efficient queries
    op.create_index('idx_events_device_timestamp', 'telemetry_events', ['device_id', sa.text('timestamp DESC')])
    op.create_index('idx_events_device_metric', 'telemetry_events', ['device_id', 'metric'])
    op.create_index('ix_telemetry_events_device_id', 'telemetry_events', ['device_id'])
    op.create_index('ix_telemetry_events_timestamp', 'telemetry_events', ['timestamp'])


def downgrade() -> None:
    """Drop telemetry_events table."""
    op.drop_index('ix_telemetry_events_timestamp', table_name='telemetry_events')
    op.drop_index('ix_telemetry_events_device_id', table_name='telemetry_events')
    op.drop_index('idx_events_device_metric', table_name='telemetry_events')
    op.drop_index('idx_events_device_timestamp', table_name='telemetry_events')
    op.drop_constraint('uq_events_device_timestamp_metric', 'telemetry_events', type_='unique')
    op.drop_table('telemetry_events')