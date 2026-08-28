import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.users.schemas import UserCreate


class DuplicateUsernameError(Exception):
    pass


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = UserRepository(session)
        self.session = session

    async def create_user(self, payload: UserCreate):
        try:
            user = await self.repository.create(payload)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateUsernameError from exc

    async def get_user(self, user_id: uuid.UUID):
        return await self.repository.get(user_id)

    async def get_users(self, offset: int = 0, limit: int = 100):
        return await self.repository.list(offset=offset, limit=limit)

