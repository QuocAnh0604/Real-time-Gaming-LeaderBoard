"""Seed a small set of users for local/manual testing."""

import asyncio
import sys
from pathlib import Path

# Allow `python scripts/seed.py` when launched from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal, engine
from app.leaderboard.models import ScoreEvent  # noqa: F401
from app.users.models import User


SEED_USERS = (
    {"username": "alice", "display_name": "Alice"},
    {"username": "bob", "display_name": "Bob"},
    {"username": "charlie", "display_name": "Charlie"},
)


async def seed_users() -> int:
    async with AsyncSessionLocal() as session:
        usernames = [user["username"] for user in SEED_USERS]
        existing = set(
            (
                await session.scalars(
                    select(User.username).where(User.username.in_(usernames))
                )
            ).all()
        )

        new_users = [
            User(**user)
            for user in SEED_USERS
            if user["username"] not in existing
        ]
        session.add_all(new_users)
        await session.commit()
        return len(new_users)


async def main() -> None:
    created = await seed_users()
    print(f"Seed complete: {created} user(s) created.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
