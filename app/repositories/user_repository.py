from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User
from app.users.schemas import UserCreate


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payload: UserCreate) -> User:
        user = User(username=payload.username, display_name=payload.display_name)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def list(self, offset: int = 0, limit: int = 100) -> list[User]:
        result = await self.session.scalars(
            select(User).order_by(User.created_at, User.id).offset(offset).limit(limit)
        )
        return list(result)

    async def get_many(self, user_ids: list[uuid.UUID]) -> list[User]:
        if not user_ids:
            return []
        result = await self.session.scalars(select(User).where(User.id.in_(user_ids)))
        return list(result)
