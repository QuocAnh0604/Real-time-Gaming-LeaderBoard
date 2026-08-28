from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.users import router as users_router
from app.api.v1.scores import router as scores_router
from app.api.v1.leaderboards import router as leaderboards_router

app = FastAPI(title="Real-Time Gaming Leaderboard")


@app.exception_handler(RedisError)
async def redis_error_handler(request: Request, exc: RedisError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Redis unavailable"})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


app.include_router(users_router, prefix="/api/v1")
app.include_router(scores_router, prefix="/api/v1")
app.include_router(leaderboards_router, prefix="/api/v1")
