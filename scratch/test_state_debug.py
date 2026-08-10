import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.models.appointment import Doctor, Department

async def check():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        docs = (await db.execute(select(Doctor))).scalars().all()
        for d in docs:
            print(f"Doctor: id={d.id}, name={d.first_name} {d.last_name}, dept_id={d.department_id}, is_active={d.is_active}")
        
        depts = (await db.execute(select(Department))).scalars().all()
        for dp in depts:
            print(f"Department: id={dp.id}, name={dp.name}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
