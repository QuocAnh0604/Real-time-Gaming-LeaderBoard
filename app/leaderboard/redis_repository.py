from redis.asyncio import Redis


class LeaderboardRedisRepository:
    def __init__(self, client: Redis) -> None:
        self.client = client

    @staticmethod
    def key(period: str) -> str:
        return f"leaderboard:{period}"

    async def increment_score(self, period: str, user_id: str, points: int) -> int:
        return int(await self.client.zincrby(self.key(period), points, user_id))

    async def get_score(self, period: str, user_id: str) -> int | None:
        score = await self.client.zscore(self.key(period), user_id)
        return None if score is None else int(score)

    async def get_rank(self, period: str, user_id: str) -> int | None:
        score = await self.get_score(period, user_id)
        if score is None:
            return None
        # Competition ranking: players with the same score share a rank.
        higher_scores = await self.client.zcount(self.key(period), f"({score}", "+inf")
        return int(higher_scores)

    async def get_top(self, period: str, limit: int) -> list[tuple[str, int]]:
        values = await self.client.zrevrange(self.key(period), 0, limit - 1, withscores=True)
        return [(str(user_id), int(score)) for user_id, score in values]

    async def get_size(self, period: str) -> int:
        return int(await self.client.zcard(self.key(period)))

    async def get_neighbors(
        self, period: str, user_id: str, radius: int
    ) -> list[tuple[str, int]]:
        position = await self.client.zrevrank(self.key(period), user_id)
        if position is None:
            return []
        start = max(0, position - radius)
        end = position + radius
        values = await self.client.zrevrange(
            self.key(period), start, end, withscores=True
        )
        return [(str(member), int(score)) for member, score in values]
