import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.users.schemas import UserCreate, UserRead
from app.users.service import DuplicateUsernameError, UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate, session: AsyncSession = Depends(get_db_session)
) -> UserRead:
    try:
        return await UserService(session).create_user(payload)
    except DuplicateUsernameError:
        raise HTTPException(status_code=409, detail="Username already exists")


@router.get("", response_model=list[UserRead])
async def list_users(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
) -> list[UserRead]:
    return await UserService(session).get_users(offset=offset, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> UserRead:
    user = await UserService(session).get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

