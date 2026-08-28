import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.period import get_current_period
from app.db.session import get_db_session
from app.leaderboard.schemas import (
    LeaderboardResponse,
    NeighborsResponse,
    PlayerRankResponse,
)
from app.leaderboard.service import LeaderboardService, PlayerNotRankedError
from app.redis.client import get_redis

router = APIRouter(prefix="/leaderboards", tags=["leaderboards"])


def _period_or_current(period: str) -> str:
    return get_current_period() if period == "current" else period


@router.get("/{period}", response_model=LeaderboardResponse)
async def get_leaderboard(
    period: str,
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> LeaderboardResponse:
    entries, total = await LeaderboardService(session, redis).get_top(
        _period_or_current(period), limit
    )
    return LeaderboardResponse(
        data=[
            {"rank": rank, "user_id": user_id, "username": username, "score": score}
            for rank, user_id, username, score in entries
        ],
        total=total,
    )


@router.get("/{period}/users/{user_id}", response_model=PlayerRankResponse)
async def get_player_rank(
    period: str,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> PlayerRankResponse:
    resolved_period = _period_or_current(period)
    try:
        rank, score = await LeaderboardService(session, redis).get_rank(
            resolved_period, user_id
        )
    except PlayerNotRankedError:
        raise HTTPException(status_code=404, detail="Player is not ranked")
    return PlayerRankResponse(
        user_id=user_id, period=resolved_period, score=score, rank=rank
    )


@router.get(
    "/{period}/users/{user_id}/neighbors", response_model=NeighborsResponse
)
async def get_player_neighbors(
    period: str,
    user_id: uuid.UUID,
    radius: int = Query(default=4, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> NeighborsResponse:
    resolved_period = _period_or_current(period)
    try:
        entries = await LeaderboardService(session, redis).get_neighbors(
            resolved_period, user_id, radius
        )
    except PlayerNotRankedError:
        raise HTTPException(status_code=404, detail="Player is not ranked")
    return NeighborsResponse(
        data=[
            {"rank": rank, "user_id": member, "username": username, "score": score}
            for rank, member, username, score in entries
        ]
    )
