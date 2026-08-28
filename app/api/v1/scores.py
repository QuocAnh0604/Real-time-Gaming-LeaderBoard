import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.common.period import get_current_period
from app.leaderboard.schemas import (
    LeaderboardResponse,
    NeighborsResponse,
    PlayerRankResponse,
    ScoreResponse,
    SubmitScoreRequest,
)
from app.leaderboard.service import (
    LeaderboardService,
    PlayerNotRankedError,
    ScoreService,
    UserNotFoundError,
)
from app.redis.client import get_redis

router = APIRouter(prefix="/scores", tags=["scores"])


@router.post("", response_model=ScoreResponse, status_code=status.HTTP_201_CREATED)
async def submit_score(
    payload: SubmitScoreRequest,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> ScoreResponse:
    try:
        period, score, rank = await ScoreService(session, redis).add_score(
            payload.user_id, payload.points
        )
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    return ScoreResponse(
        user_id=payload.user_id, period=period, score=score, rank=rank
    )


@router.get("", response_model=LeaderboardResponse)
async def get_current_leaderboard(
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> LeaderboardResponse:
    entries, total = await LeaderboardService(session, redis).get_top(
        get_current_period(), limit
    )
    return LeaderboardResponse(
        data=[
            {"rank": rank, "user_id": user_id, "username": username, "score": score}
            for rank, user_id, username, score in entries
        ],
        total=total,
    )


@router.get("/{user_id}", response_model=PlayerRankResponse)
async def get_current_player_rank(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> PlayerRankResponse:
    period = get_current_period()
    try:
        rank, score = await LeaderboardService(session, redis).get_rank(period, user_id)
    except PlayerNotRankedError:
        raise HTTPException(status_code=404, detail="Player is not ranked")
    return PlayerRankResponse(user_id=user_id, period=period, score=score, rank=rank)


@router.get("/{user_id}/neighbors", response_model=NeighborsResponse)
async def get_current_player_neighbors(
    user_id: uuid.UUID,
    radius: int = Query(default=4, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> NeighborsResponse:
    period = get_current_period()
    try:
        entries = await LeaderboardService(session, redis).get_neighbors(
            period, user_id, radius
        )
    except PlayerNotRankedError:
        raise HTTPException(status_code=404, detail="Player is not ranked")
    return NeighborsResponse(
        data=[
            {"rank": rank, "user_id": member, "username": username, "score": score}
            for rank, member, username, score in entries
        ]
    )
