import uuid

from pydantic import BaseModel, Field


class SubmitScoreRequest(BaseModel):
    user_id: uuid.UUID
    points: int = Field(gt=0)


class ScoreResponse(BaseModel):
    user_id: uuid.UUID
    period: str
    score: int
    rank: int


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: uuid.UUID
    username: str
    score: int


class LeaderboardResponse(BaseModel):
    data: list[LeaderboardEntry]
    total: int


class PlayerRankResponse(BaseModel):
    user_id: uuid.UUID
    period: str
    score: int
    rank: int


class NeighborsResponse(BaseModel):
    data: list[LeaderboardEntry]
