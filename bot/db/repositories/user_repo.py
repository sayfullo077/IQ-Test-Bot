from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.user import User

PAGE_SIZE = 5


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, username: str | None, full_name: str) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.username = username
            user.full_name = full_name
            await self.session.flush()
            return user, False
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        self.session.add(user)
        await self.session.flush()
        return user, True

    async def get_page(self, page: int = 0) -> list[User]:
        result = await self.session.execute(
            select(User)
            .order_by(User.created_at.desc())
            .offset(page * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(User))
        return result.scalar_one()

    async def get_all_ids(self) -> list[int]:
        result = await self.session.execute(
            select(User.telegram_id).where(User.is_banned.is_(False))
        )
        return list(result.scalars().all())

    async def ban(self, user: User) -> None:
        user.is_banned = True
        await self.session.flush()

    async def unban(self, user: User) -> None:
        user.is_banned = False
        await self.session.flush()

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.flush()

    async def update(self, user: User, **kwargs) -> User:
        for k, v in kwargs.items():
            setattr(user, k, v)
        await self.session.flush()
        return user
