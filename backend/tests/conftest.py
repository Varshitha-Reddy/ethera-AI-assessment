import os

os.environ.update(
    DATABASE_URL="sqlite+aiosqlite:////tmp/ethera-test.db",
    ENABLE_CACHE="false",
    KAFKA_ENABLED="false",
    ENABLE_AUTH="true",
    RATE_LIMIT_ENABLED="false",
    JWT_SECRET="test-secret-not-for-production",
)

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import Base, engine
from app.main import app
from app.security import create_access_token


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


@pytest_asyncio.fixture
def admin_headers():
    return {"Authorization": f"Bearer {create_access_token('test-admin', 'admin')}"}


@pytest_asyncio.fixture
def editor_headers():
    return {"Authorization": f"Bearer {create_access_token('test-editor', 'editor')}"}


@pytest_asyncio.fixture
def viewer_headers():
    return {"Authorization": f"Bearer {create_access_token('test-viewer', 'viewer')}"}
