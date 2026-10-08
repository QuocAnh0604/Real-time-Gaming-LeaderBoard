from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.leaderboard.models import ScoreEvent


async def rebuild_period(
    session: AsyncSession,
    redis: Redis,
    period: str,
    batch_size: int = 1000,
    ttl_seconds: int | None = None,
) -> int:
    """Reconstruct one Redis leaderboard from the persisted score events."""
    live_key = f"leaderboard:{period}"
    temp_key = f"{live_key}:rebuild"
    await redis.delete(temp_key)
    statement = (
        select(ScoreEvent.user_id, func.sum(ScoreEvent.points).label("score"))
        .where(ScoreEvent.leaderboard_period == period)
        .group_by(ScoreEvent.user_id)
        .order_by(ScoreEvent.user_id)
    )

    count = 0
    result = await session.stream(statement)
    try:
        async for partition in result.partitions(batch_size):
            scores = {
                str(user_id): int(score)
                for user_id, score in partition
            }
            if scores:
                await redis.zadd(temp_key, scores)
                count += len(scores)
    finally:
        await result.close()

    if count == 0:
        await redis.delete(temp_key, live_key)
        return 0

    if ttl_seconds is not None:
        await redis.expire(temp_key, ttl_seconds)
    await redis.rename(temp_key, live_key)
    return count


async def list_periods(session: AsyncSession) -> list[str]:
    result = await session.scalars(
        select(ScoreEvent.leaderboard_period)
        .distinct()
        .order_by(ScoreEvent.leaderboard_period)
    )
    return list(result)
