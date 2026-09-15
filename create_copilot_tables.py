import asyncio
from app.database.session import async_engine, async_session_factory
from app.database.declarative import Base
import app.database.models.copilot
from sqlalchemy import text

async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")

    async with async_session_factory() as session:
        res = await session.execute(text("SHOW TABLES LIKE 'copilot%'"))
        print("Copilot tables in MySQL:", res.fetchall())

if __name__ == "__main__":
    asyncio.run(main())
