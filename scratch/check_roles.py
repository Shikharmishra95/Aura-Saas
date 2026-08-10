import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.models.call_log import User, Role, UserRole

async def check():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        u_stmt = select(User).where(User.username == "shiva9532")
        u = (await db.execute(u_stmt)).scalar_one_or_none()
        if u:
            print(f"User shiva9532: id={u.id}, hospital_id={u.hospital_id}")
            ur_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == u.id)
            roles = (await db.execute(ur_stmt)).scalars().all()
            print(f"Roles: {roles}")
        else:
            print("User shiva9532 not found!")
            
        print("\nAll Users:")
        all_u = (await db.execute(select(User))).scalars().all()
        for user in all_u:
            ur_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
            roles = (await db.execute(ur_stmt)).scalars().all()
            print(f"User {user.username}: id={user.id}, roles={roles}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
