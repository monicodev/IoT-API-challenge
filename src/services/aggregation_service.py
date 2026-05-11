"""Aggregation service - handles time-based aggregations."""
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.aggregate import AggregationType, IntervalType


AGG_WHITELIST: dict[AggregationType, str] = {
    AggregationType.AVG: "AVG",
    AggregationType.MIN: "MIN",
    AggregationType.MAX: "MAX",
    AggregationType.SUM: "SUM",
    AggregationType.COUNT: "COUNT",
}


class AggregationService:
    """Service for handling telemetry data aggregation."""

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

        Uses parameterized queries with whitelisted aggregation functions
        to prevent SQL injection. Timezone-aware timestamps.
        """
        agg_func = AGG_WHITELIST[aggregation]

        if interval == IntervalType.FIVE_MINUTES:
            sql = text("""
                SELECT
                    bucket,
                    """ + agg_func + """(value) AS value
                FROM (
                    SELECT
                        date_trunc('minute', timestamp) -
                        (EXTRACT(MINUTE FROM timestamp)::int % 5) * interval '1 minute' AS bucket,
                        value
                    FROM telemetry_events
                    WHERE device_id = :device_id
                        AND metric = :metric
                        AND timestamp >= :from_time
                        AND timestamp < :to_time
                ) AS bucketed
                GROUP BY bucket
                ORDER BY bucket
            """)
        elif interval == IntervalType.MINUTE:
            sql = text("""
                SELECT
                    date_trunc('minute', timestamp) AS bucket,
                    """ + agg_func + """(value) AS value
                FROM telemetry_events
                WHERE device_id = :device_id
                    AND metric = :metric
                    AND timestamp >= :from_time
                    AND timestamp < :to_time
                GROUP BY date_trunc('minute', timestamp)
                ORDER BY bucket
            """)
        elif interval == IntervalType.HOUR:
            sql = text("""
                SELECT
                    date_trunc('hour', timestamp) AS bucket,
                    """ + agg_func + """(value) AS value
                FROM telemetry_events
                WHERE device_id = :device_id
                    AND metric = :metric
                    AND timestamp >= :from_time
                    AND timestamp < :to_time
                GROUP BY date_trunc('hour', timestamp)
                ORDER BY bucket
            """)
        elif interval == IntervalType.DAY:
            sql = text("""
                SELECT
                    date_trunc('day', timestamp) AS bucket,
                    """ + agg_func + """(value) AS value
                FROM telemetry_events
                WHERE device_id = :device_id
                    AND metric = :metric
                    AND timestamp >= :from_time
                    AND timestamp < :to_time
                GROUP BY date_trunc('day', timestamp)
                ORDER BY bucket
            """)
        else:
            sql = text("""
                SELECT
                    date_trunc('hour', timestamp) AS bucket,
                    """ + agg_func + """(value) AS value
                FROM telemetry_events
                WHERE device_id = :device_id
                    AND metric = :metric
                    AND timestamp >= :from_time
                    AND timestamp < :to_time
                GROUP BY date_trunc('hour', timestamp)
                ORDER BY bucket
            """)

        result = await session.execute(
            sql,
            {
                "device_id": device_id,
                "metric": metric,
                "from_time": from_time,
                "to_time": to,
            }
        )

        rows = result.fetchall()
        return [(row[0], float(row[1])) for row in rows]