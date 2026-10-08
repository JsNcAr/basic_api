"""
General utility functions.
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """
    Return the current time as an aware UTC datetime.

    SQLModel (since 0.0.45) maps `datetime` fields to UTCDateTime, a
    TIMESTAMP WITH TIME ZONE column that refuses naive values at bind time and
    returns aware UTC values on read. Every timestamp the app stores, compares
    or puts in a token goes through this function, so there is one convention:
    aware, UTC. Responses carry the zone ("...Z") for the same reason.

    Returns:
        The current time with tzinfo set to UTC (the 3.11+ alias of timezone.utc).
    """
    return datetime.now(UTC)
