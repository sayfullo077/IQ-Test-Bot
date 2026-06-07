from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.module import Module


class ModuleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, active_only: bool = False) -> list[Module]:
        q = select(Module).order_by(Module.order, Module.id)
        if active_only:
            q = q.where(Module.is_active.is_(True))
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, module_id: int) -> Module | None:
        result = await self.session.execute(select(Module).where(Module.id == module_id))
        return result.scalar_one_or_none()

    async def create(self, name: str, description: str | None = None, order: int = 0) -> Module:
        module = Module(name=name, description=description, order=order)
        self.session.add(module)
        await self.session.flush()
        return module

    async def update(self, module: Module, **kwargs) -> Module:
        for k, v in kwargs.items():
            setattr(module, k, v)
        await self.session.flush()
        return module

    async def delete(self, module: Module) -> None:
        await self.session.delete(module)
        await self.session.flush()
