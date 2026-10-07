"""
General utility functions.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Return the current UTC time as a naive datetime.

    The columns are TIMESTAMP WITHOUT TIME ZONE, which asyncpg will only accept
    naive values for, and datetime.utcnow() is deprecated since Python 3.12.
    Every timestamp the app stores or compares goes through this function.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
