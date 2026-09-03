import os
import sys
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from sqlalchemy import select
from passlib.context import CryptContext
from app.database.session import async_session_factory
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Hospital

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_users():
    print("Seeding default authentication users in local MySQL aaa_db...")
    async with async_session_factory() as db:
        # 1. Seed Roles
        roles_dict = {}
        for role_name in ["SUPER_ADMIN", "ADMIN", "DOCTOR", "RECEPTIONIST"]:
            r_stmt = select(Role).where(Role.name == role_name)
            r = (await db.execute(r_stmt)).scalar_one_or_none()
            if not r:
                r = Role(id=f"role_{role_name.lower()}", name=role_name, description=f"{role_name} Access Level")
                db.add(r)
                await db.flush()
            roles_dict[role_name] = r.id
        
        print("Roles verified/created:", roles_dict)

        # Get default hospital
        h_stmt = select(Hospital).where(Hospital.id == "hosp_default")
        hospital = (await db.execute(h_stmt)).scalar_one_or_none()
        hosp_id = hospital.id if hospital else "hosp_default"

        # 2. Seed Users
        users_to_seed = [
            {"username": "owner", "email": "owner@aurasaas.com", "role": "SUPER_ADMIN", "hosp_id": hosp_id},
            {"username": "BALAJI932", "email": "admin@cptiwari.com", "role": "ADMIN", "hosp_id": hosp_id},
            {"username": "recep", "email": "receptionist@cptiwari.com", "role": "RECEPTIONIST", "hosp_id": hosp_id},
            {"username": "cptiwari", "email": "cptiwari@cptiwari.com", "role": "DOCTOR", "hosp_id": hosp_id},
        ]

        hashed_pwd = pwd_context.hash("password123")

        for u_data in users_to_seed:
            u_stmt = select(User).where(User.username == u_data["username"])
            u = (await db.execute(u_stmt)).scalar_one_or_none()
            if not u:
                user_id = f"user_{u_data['username'].lower()}"
                u = User(
                    id=user_id,
                    username=u_data["username"],
                    email=u_data["email"],
                    password_hash=hashed_pwd,
                    hospital_id=u_data["hosp_id"],
                    is_active=True
                )
                db.add(u)
                await db.flush()
                
                # Assign Role
                ur = UserRole(id=f"ur_{u_data['username'].lower()}", user_id=u.id, role_id=roles_dict[u_data["role"]])
                db.add(ur)
                print(f"Created user '{u_data['username']}' with role '{u_data['role']}' and password 'password123'.")
            else:
                u.password_hash = hashed_pwd
                print(f"User '{u_data['username']}' already exists. Reset password to 'password123'.")

        await db.commit()
        print("Default authentication users seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_users())
