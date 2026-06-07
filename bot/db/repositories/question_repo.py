from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.question import Question


class QuestionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_module(self, module_id: int) -> list[Question]:
        result = await self.session.execute(
            select(Question).where(Question.module_id == module_id).order_by(Question.order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, question_id: int) -> Question | None:
        result = await self.session.execute(select(Question).where(Question.id == question_id))
        return result.scalar_one_or_none()

    async def get_by_module_order(self, module_id: int, order: int) -> Question | None:
        result = await self.session.execute(
            select(Question).where(Question.module_id == module_id, Question.order == order)
        )
        return result.scalar_one_or_none()

    async def count_by_module(self, module_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Question).where(Question.module_id == module_id)
        )
        return result.scalar_one()

    async def create(
        self,
        module_id: int,
        order: int,
        correct_answer: str,
        options_count: int,
        image_path: str | None = None,
        image_file_id: str | None = None,
        q_type: str | None = None,
        difficulty: str | None = None,
    ) -> Question:
        q = Question(
            module_id=module_id,
            order=order,
            correct_answer=correct_answer.upper(),
            options_count=options_count,
            image_path=image_path,
            image_file_id=image_file_id,
            q_type=q_type,
            difficulty=difficulty,
        )
        self.session.add(q)
        await self.session.flush()
        return q

    async def update(self, question: Question, **kwargs) -> Question:
        for k, v in kwargs.items():
            setattr(question, k, v)
        await self.session.flush()
        return question

    async def delete(self, question: Question) -> None:
        await self.session.delete(question)
        await self.session.flush()

    async def cache_file_id(self, question: Question, file_id: str) -> None:
        question.image_file_id = file_id
        await self.session.flush()
