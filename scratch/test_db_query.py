import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.models.appointment import Doctor

async def check():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        candidate_ids = ["53224cae-13cf-42ac-8e4b-04ead468bef7", "cfec1f77-4747-4709-8cd3-79473d4b7934"]
        doc_stmt = select(Doctor).where(Doctor.id.in_(candidate_ids))
        cand_doctors = (await db.execute(doc_stmt)).scalars().all()
        print(f"Results matching candidate_ids: {cand_doctors}")
        for d in cand_doctors:
            print(f"Match: id={d.id}, name={d.first_name} {d.last_name}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
