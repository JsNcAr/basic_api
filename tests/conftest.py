"""
Test fixtures. Database tests run against a throwaway PostgreSQL database built
from DB_* and TEST_DB_NAME (see docs/setup.md); tests that need none import the
code directly and can run with `pytest --noconftest`.

Adapting this starter: the four `from basic_api ...` imports below are the only
project-specific lines; rename them with the package. The DB_* defaults are for
a developer's own PostgreSQL and are overridden by the environment in CI
(.github/workflows/ci.yml), so they need no change.
"""

import asyncio
import os
from typing import AsyncGenerator

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

load_dotenv()

from basic_api.auth import create_access_token, get_password_hash  # noqa: E402
from basic_api.database import get_session  # noqa: E402
from basic_api.main import app  # noqa: E402
from basic_api.schemas.user import User  # noqa: E402

db_user = os.getenv("DB_USER", "postgres")
db_pass = os.getenv("DB_PASSWORD", "postgres")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
test_db_name = os.getenv("TEST_DB_NAME", "basic_api_test_db")
api_key = os.getenv("API_KEY", "test-api-key")

TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/{test_db_name}"
)

engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
async_session_maker = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


def pytest_configure(config):
    """Create the tables once per run."""

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    asyncio.run(setup())


def pytest_unconfigure(config):
    """Drop them at the end, leaving the test database clean."""

    async def teardown():
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)

    asyncio.run(teardown())


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """A session per test; every row is deleted afterwards."""
    async with async_session_maker() as session:
        yield session
        await session.rollback()

    async with async_session_maker() as cleanup:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await cleanup.execute(table.delete())
        await cleanup.commit()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client over the app, sharing the test session and sending the API key."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": api_key},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(session: AsyncSession) -> User:
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}
