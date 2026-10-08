import fakeredis.aioredis
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.leaderboard.models import ScoreEvent
from app.leaderboard.rebuild import list_periods, rebuild_period
from app.users.models import User


@pytest_asyncio.fixture
async def rebuild_context():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    async with session_factory() as session:
        yield session, redis
    await redis.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_rebuild_period_replaces_board_and_lists_periods(rebuild_context):
    session, redis = rebuild_context
    first = User(username="alice", display_name="Alice")
    second = User(username="bob", display_name="Bob")
    session.add_all([first, second])
    await session.flush()
    session.add_all(
        [
            ScoreEvent(user_id=first.id, points=2, leaderboard_period="2026-10"),
            ScoreEvent(user_id=first.id, points=3, leaderboard_period="2026-10"),
            ScoreEvent(user_id=second.id, points=4, leaderboard_period="2026-10"),
        ]
    )
    await session.commit()
    await redis.zadd(
        "leaderboard:2026-10", {str(first.id): 99, str(second.id): 1}
    )

    assert await rebuild_period(session, redis, "2026-10", batch_size=1) == 2
    assert await redis.zrevrange("leaderboard:2026-10", 0, -1, withscores=True) == [
        (str(first.id), 5.0),
        (str(second.id), 4.0),
    ]
    assert await list_periods(session) == ["2026-10"]


@pytest.mark.asyncio
async def test_rebuild_empty_period_deletes_live_board(rebuild_context):
    session, redis = rebuild_context
    await redis.zadd("leaderboard:2026-11", {"stale-user": 10})

    assert await rebuild_period(session, redis, "2026-11") == 0
    assert not await redis.exists("leaderboard:2026-11")
