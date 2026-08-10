import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.models.appointment import HospitalSetting
from app.database.models.call_log import User

async def check():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Get user id of recep
        u_stmt = select(User).where(User.username == "recep")
        u = (await db.execute(u_stmt)).scalar_one_or_none()
        if u:
            print(f"Recep user ID: {u.id}")
            pwd_stmt = select(HospitalSetting).where(
                HospitalSetting.setting_key == f"staff_pwd_{u.id}"
            )
            row = (await db.execute(pwd_stmt)).scalar_one_or_none()
            if row:
                print(f"Password stored in settings table for recep: '{row.setting_value}'")
                print(f"Hashed password in users table for recep: '{u.password_hash}'")
            else:
                print(f"No HospitalSetting staff_pwd_{u.id} found!")
        else:
            print("User recep not found in DB!")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
