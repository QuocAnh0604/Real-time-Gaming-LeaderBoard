import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.leaderboard.models import ScoreEvent


class ScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_event(
        self, user_id: uuid.UUID, points: int, leaderboard_period: str
    ) -> ScoreEvent:
        event = ScoreEvent(
            user_id=user_id,
            points=points,
            leaderboard_period=leaderboard_period,
        )
        self.session.add(event)
        await self.session.flush()
        return event
