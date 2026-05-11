"""Aggregation service - handles time-based aggregations."""
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.aggregate import AggregationType, IntervalType


class AggregationService:
    """Service for handling telemetry data aggregation."""

    # Mapping from interval to PostgreSQL date_trunc unit
    INTERVAL_TO_TRUNC = {
        IntervalType.MINUTE: "minute",
        IntervalType.FIVE_MINUTES: "minute",  # We'll handle 5m separately
        IntervalType.HOUR: "hour",
        IntervalType.DAY: "day",
    }

    # Mapping from aggregation type to SQL function
    AGG_TO_SQL = {
        AggregationType.AVG: "AVG(value)",
        AggregationType.MIN: "MIN(value)",
        AggregationType.MAX: "MAX(value)",
        AggregationType.SUM: "SUM(value)",
        AggregationType.COUNT: "COUNT(*)",
    }

    @staticmethod
    async def get_aggregation(
        session: AsyncSession,
        device_id: str,
        metric: str,
        from_time: datetime,
        to: datetime,
        interval: IntervalType,
        aggregation: AggregationType,
    ) -> List[Tuple[datetime, float]]:
        """
        Get aggregated telemetry data using PostgreSQL date_trunc.

        Uses efficient PostgreSQL aggregation with proper index usage.
        """
        # Determine the truncation and interval adjustments
        trunc_unit = AggregationService.INTERVAL_TO_TRUNC.get(interval, "hour")
        agg_func = AggregationService.AGG_TO_SQL[aggregation]

        # Build the SQL query with the aggregation function embedded
        if interval == IntervalType.FIVE_MINUTES:
            sql = text("""
                SELECT
                    date_trunc('minute', timestamp) - 
                    (EXTRACT(MINUTE FROM timestamp)::int % 5) * interval '1 minute' AS bucket,
                    """ + agg_func + """ AS value
                FROM telemetry_events
                WHERE device_id = :device_id
                    AND metric = :metric
                    AND timestamp >= :from_time
                    AND timestamp < :to_time
                GROUP BY bucket
                ORDER BY bucket
            """)
        else:
            sql = text("""
                SELECT
                    date_trunc(:trunc_unit, timestamp) AS bucket,
                    """ + agg_func + """ AS value
                FROM telemetry_events
                WHERE device_id = :device_id
                    AND metric = :metric
                    AND timestamp >= :from_time
                    AND timestamp < :to_time
                GROUP BY bucket
                ORDER BY bucket
            """)

        # Execute with proper parameter binding
        if interval == IntervalType.FIVE_MINUTES:
            result = await session.execute(
                sql,
                {
                    "device_id": device_id,
                    "metric": metric,
                    "from_time": from_time,
                    "to_time": to,
                }
            )
        else:
            result = await session.execute(
                sql,
                {
                    "device_id": device_id,
                    "metric": metric,
                    "from_time": from_time,
                    "to_time": to,
                    "trunc_unit": trunc_unit,
                }
            )

        rows = result.fetchall()
        return [(row[0], float(row[1])) for row in rows]