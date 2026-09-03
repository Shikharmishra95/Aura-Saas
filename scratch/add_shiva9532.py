import os
import sys
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from sqlalchemy import select
from passlib.context import CryptContext
from app.database.session import async_session_factory
from app.database.models.call_log import User, Role, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def add_shiva_user():
    async with async_session_factory() as db:
        r_stmt = select(Role).where(Role.name == "SUPER_ADMIN")
        r = (await db.execute(r_stmt)).scalar_one_or_none()
        if not r:
            r = Role(id="role_super_admin", name="SUPER_ADMIN", description="SUPER_ADMIN Access Level")
            db.add(r)
            await db.flush()

        hashed_pwd = pwd_context.hash("12345678") # set password for shiva9532 to 12345678 or password123
        
        # Check shiva9532
        u_stmt = select(User).where(User.username == "shiva9532")
        u = (await db.execute(u_stmt)).scalar_one_or_none()
        if not u:
            u = User(
                id="user_shiva9532",
                username="shiva9532",
                email="shiva9532@aurasaas.com",
                password_hash=hashed_pwd,
                hospital_id="hosp_default",
                is_active=True
            )
            db.add(u)
            await db.flush()
            ur = UserRole(id="ur_shiva9532", user_id=u.id, role_id=r.id)
            db.add(ur)
            print("Successfully created 'shiva9532' Super Admin user account!")
        else:
            u.password_hash = hashed_pwd
            print("User 'shiva9532' already exists. Password updated to '12345678'.")

        await db.commit()

if __name__ == "__main__":
    asyncio.run(add_shiva_user())
