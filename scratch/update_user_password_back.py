import asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.models.call_log import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def update_pwd():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        hashed = pwd_context.hash("112233")
        stmt = update(User).where(User.username == "recep").values(password_hash=hashed)
        await db.execute(stmt)
        await db.commit()
        print("Updated password for 'recep' back to '112233' to match settings table!")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(update_pwd())
