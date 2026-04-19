import os

os.environ["TESTING"] = "true"
# Force a RFC 7518-compliant HMAC key (>=32 bytes) in tests.
# This overrides any short key set in CI or local environment variables.
_TEST_JWT_KEY = "test-jwt-secret-key-minimum-32-bytes-long!"  # noqa: S105
os.environ["JWT_SECRET_KEY"] = _TEST_JWT_KEY

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import cache
from app.database import Base, get_db
from app.models import Resource, User
from app.utils.auth import create_access_token, create_refresh_token

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture
async def client(db):
    async def override_get_db():
        yield db

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    mock_redis.keys.return_value = []
    mock_redis.delete.return_value = 1
    mock_redis.ping.return_value = True
    cache.redis_client = mock_redis

    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db):
    user = User(name="Test User", email="test@example.com")
    user.set_password("password123")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_user(db):
    user = User(name="Admin User", email="admin@example.com", role="admin")
    user.set_password("password123")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def refresh_headers(test_user):
    token = create_refresh_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_resource(db):
    resource = Resource(name="Boardroom A", description="Main boardroom", capacity=10)
    db.add(resource)
    await db.flush()
    await db.refresh(resource)
    return resource


@pytest.fixture
def future_times():
    from datetime import datetime, timedelta

    start = datetime.now() + timedelta(days=1)
    end = start + timedelta(hours=1)
    return start.strftime("%Y-%m-%dT%H:%M:%S"), end.strftime("%Y-%m-%dT%H:%M:%S")
