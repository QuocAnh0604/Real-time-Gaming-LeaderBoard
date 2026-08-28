import uuid

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.redis.client import get_redis
from app.leaderboard.models import ScoreEvent  # noqa: F401
from app.users.models import User  # noqa: F401


@pytest_asyncio.fixture
async def leaderboard_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def override_session():
        async with session_factory() as session:
            yield session

    async def override_redis():
        yield redis

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_redis] = override_redis
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
    await redis.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_submit_score_and_read_leaderboard(leaderboard_client):
    created = await leaderboard_client.post(
        "/api/v1/users", json={"username": "alice", "display_name": "Alice"}
    )
    user_id = uuid.UUID(created.json()["id"])

    first = await leaderboard_client.post(
        "/api/v1/scores", json={"user_id": str(user_id), "points": 5}
    )
    second = await leaderboard_client.post(
        "/api/v1/scores", json={"user_id": str(user_id), "points": 3}
    )
    assert first.status_code == 201
    assert second.json()["score"] == 8
    assert second.json()["rank"] == 1

    leaderboard = await leaderboard_client.get("/api/v1/leaderboards/current")
    assert leaderboard.status_code == 200
    assert leaderboard.json()["data"][0]["score"] == 8
    assert leaderboard.json()["total"] == 1

    rank = await leaderboard_client.get(
        f"/api/v1/leaderboards/current/users/{user_id}"
    )
    assert rank.json()["rank"] == 1


@pytest.mark.asyncio
async def test_submit_score_requires_existing_user(leaderboard_client):
    response = await leaderboard_client.post(
        "/api/v1/scores",
        json={"user_id": str(uuid.uuid4()), "points": 1},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_submit_score_rejects_non_positive_points(leaderboard_client):
    response = await leaderboard_client.post(
        "/api/v1/scores",
        json={"user_id": str(uuid.uuid4()), "points": 0},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_neighbors_are_clamped_to_leaderboard_edges(leaderboard_client):
    user_ids = []
    for username, points in (("alice", 30), ("bob", 20), ("charlie", 10)):
        created = await leaderboard_client.post(
            "/api/v1/users",
            json={"username": username, "display_name": username.title()},
        )
        user_id = created.json()["id"]
        user_ids.append(user_id)
        await leaderboard_client.post(
            "/api/v1/scores", json={"user_id": user_id, "points": points}
        )

    neighbors = await leaderboard_client.get(
        f"/api/v1/leaderboards/current/users/{user_ids[0]}/neighbors?radius=4"
    )
    assert neighbors.status_code == 200
    assert [entry["username"] for entry in neighbors.json()["data"]] == [
        "alice",
        "bob",
        "charlie",
    ]


@pytest.mark.asyncio
async def test_players_with_equal_scores_share_rank(leaderboard_client):
    user_ids = []
    for username in ("alice", "bob"):
        created = await leaderboard_client.post(
            "/api/v1/users",
            json={"username": username, "display_name": username.title()},
        )
        user_id = created.json()["id"]
        user_ids.append(user_id)
        await leaderboard_client.post(
            "/api/v1/scores", json={"user_id": user_id, "points": 10}
        )

    for user_id in user_ids:
        response = await leaderboard_client.get(f"/api/v1/scores/{user_id}")
        assert response.json()["rank"] == 1
