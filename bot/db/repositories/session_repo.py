from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.session import TestSession
from bot.db.models.user import User


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, module_id: int) -> TestSession:
        s = TestSession(user_id=user_id, module_id=module_id, answers={})
        self.session.add(s)
        await self.session.flush()
        return s

    async def get_by_id(self, session_id: int) -> TestSession | None:
        result = await self.session.execute(select(TestSession).where(TestSession.id == session_id))
        return result.scalar_one_or_none()

    async def finish(self, test_session: TestSession, score: int, iq_score: int, answers: dict) -> TestSession:
        test_session.finished_at = datetime.now(timezone.utc)
        test_session.score = score
        test_session.iq_score = iq_score
        test_session.answers = answers
        await self.session.flush()
        return test_session

    async def get_user_sessions(self, user_id: int) -> list[TestSession]:
        result = await self.session.execute(
            select(TestSession)
            .where(TestSession.user_id == user_id)
            .order_by(TestSession.started_at.desc())
        )
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 20) -> list[TestSession]:
        result = await self.session.execute(
            select(TestSession)
            .where(TestSession.finished_at.isnot(None))
            .order_by(TestSession.finished_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
