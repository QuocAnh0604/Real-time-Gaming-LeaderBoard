import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.leaderboard.models import ScoreEvent  # noqa: F401
from app.users.models import User  # noqa: F401


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_retrieve_user(client):
    response = await client.post(
        "/api/v1/users", json={"username": "alice", "display_name": "Alice"}
    )
    assert response.status_code == 201
    user = response.json()
    assert user["username"] == "alice"
    assert user["display_name"] == "Alice"
    assert uuid.UUID(user["id"])

    fetched = await client.get(f"/api/v1/users/{user['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == user["id"]


@pytest.mark.asyncio
async def test_list_users_and_duplicate_username(client):
    await client.post("/api/v1/users", json={"username": "alice", "display_name": "Alice"})
    duplicate = await client.post(
        "/api/v1/users", json={"username": "alice", "display_name": "Another Alice"}
    )
    assert duplicate.status_code == 409

    listed = await client.get("/api/v1/users")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
