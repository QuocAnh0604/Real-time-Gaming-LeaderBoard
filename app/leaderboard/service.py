import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.period import get_current_period
from app.leaderboard.redis_repository import LeaderboardRedisRepository
from app.repositories.score_repository import ScoreRepository
from app.repositories.user_repository import UserRepository


class UserNotFoundError(Exception):
    pass


class PlayerNotRankedError(Exception):
    pass


class ScoreService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.scores = ScoreRepository(session)
        self.leaderboard = LeaderboardRedisRepository(redis)

    async def add_score(self, user_id: uuid.UUID, points: int) -> tuple[str, int, int]:
        if await self.users.get(user_id) is None:
            raise UserNotFoundError
        period = get_current_period()
        await self.scores.create_event(user_id, points, period)
        await self.session.commit()
        score = await self.leaderboard.increment_score(period, str(user_id), points)
        rank = await self.leaderboard.get_rank(period, str(user_id))
        assert rank is not None
        return period, score, rank + 1


class LeaderboardService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.users = UserRepository(session)
        self.leaderboard = LeaderboardRedisRepository(redis)

    async def get_top(self, period: str, limit: int):
        ranked = await self.leaderboard.get_top(period, limit)
        users = await self.users.get_many([uuid.UUID(user_id) for user_id, _ in ranked])
        by_id = {str(user.id): user for user in users}
        entries = []
        for user_id, score in ranked:
            if user_id in by_id:
                rank = await self.leaderboard.get_rank(period, user_id)
                entries.append(
                    (rank + 1, uuid.UUID(user_id), by_id[user_id].username, score)
                )
        return entries, await self.leaderboard.get_size(period)

    async def get_rank(self, period: str, user_id: uuid.UUID):
        rank = await self.leaderboard.get_rank(period, str(user_id))
        score = await self.leaderboard.get_score(period, str(user_id))
        if rank is None or score is None:
            raise PlayerNotRankedError
        return rank + 1, score

    async def get_neighbors(self, period: str, user_id: uuid.UUID, radius: int):
        ranked = await self.leaderboard.get_neighbors(period, str(user_id), radius)
        if not ranked:
            raise PlayerNotRankedError
        users = await self.users.get_many([uuid.UUID(item[0]) for item in ranked])
        by_id = {str(user.id): user for user in users}
        entries = []
        for member, score in ranked:
            if member in by_id:
                rank = await self.leaderboard.get_rank(period, member)
                entries.append(
                    (rank + 1, uuid.UUID(member), by_id[member].username, score)
                )
        return entries
