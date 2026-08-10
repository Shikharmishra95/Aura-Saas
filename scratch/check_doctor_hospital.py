import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.models.appointment import Doctor, Hospital

async def check():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        docs = (await db.execute(select(Doctor))).scalars().all()
        for d in docs:
            print(f"Doctor: id={d.id}, name={d.first_name} {d.last_name}, hosp_id={d.hospital_id}")
        
        hosps = (await db.execute(select(Hospital))).scalars().all()
        for h in hosps:
            print(f"Hospital: id={h.id}, name={h.name}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
