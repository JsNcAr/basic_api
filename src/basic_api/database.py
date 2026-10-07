"""
Database engine, session factory, startup schema and health ping.
"""

import asyncio
import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import DATABASE_ECHO, DATABASE_URL
from .schemas import user as _user_models  # noqa: F401  registers the tables

logger = logging.getLogger(__name__)

# pool_pre_ping checks a pooled connection with a trivial query before handing
# it out, so a database restart costs one silent reconnect, not a failed request.
engine = create_async_engine(DATABASE_URL, echo=DATABASE_ECHO, pool_pre_ping=True)

# expire_on_commit=False keeps loaded attributes readable after a commit, which
# the routers rely on when they build responses from objects just committed.
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """
    Create any missing tables from the SQLModel metadata.

    create_all adds tables that do not exist and never alters existing ones. It
    is the right tool for a starter; once the schema changes under live data,
    replace this with Alembic migrations run as a deploy step.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def ping(timeout: float = 2.0) -> bool:
    """
    Whether the database answers, for the health check.

    Args:
        timeout: Seconds to wait before reporting the database as down.

    Returns:
        True if "SELECT 1" succeeds within the timeout, False otherwise. Never
        raises: the health endpoint turns False into a 503.
    """
    try:
        async with asyncio.timeout(timeout):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("Database ping failed: %s", e)
        return False


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """One session per request; closed when the request ends."""
    async with async_session_factory() as session:
        yield session
