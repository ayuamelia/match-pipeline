import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pelgo:pelgo_secret@localhost:5432/pelgo_test",
)

TEST_CANDIDATE_ID = str(uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"))


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    from app.database import Base

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seeded_candidate(db_session: AsyncSession):
    import json

    from sqlalchemy import text

    await db_session.execute(
        text("""
            INSERT INTO candidates (
                id, name, email, location, willing_to_relocate,
                years_of_experience, seniority_level, skills, summary
            ) VALUES (
                :id::uuid, :name, :email, :location, :willing,
                :years, :seniority, :skills::jsonb, :summary
            )
            ON CONFLICT (email) DO NOTHING
        """),
        {
            "id": TEST_CANDIDATE_ID,
            "name": "Test Candidate",
            "email": "test@pelgo.test",
            "location": "Singapore",
            "willing": True,
            "years": 7,
            "seniority": "senior",
            "skills": json.dumps(["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"]),
            "summary": "Test candidate for integration tests.",
        },
    )
    await db_session.commit()
    return TEST_CANDIDATE_ID


@pytest.fixture
def override_settings():
    from app.config import Settings

    return Settings(
        database_url=TEST_DATABASE_URL,
        secret_key="test_secret_key_minimum_32_characters_long",
        candidate_id=TEST_CANDIDATE_ID,
        redis_url="redis://localhost:6379/1",
    )


@pytest_asyncio.fixture
async def client(override_settings, seeded_candidate) -> AsyncGenerator[AsyncClient, None]:
    from app.config import get_settings
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: override_settings

    from app.worker import celery_app
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    celery_app.conf.update(task_always_eager=False)
