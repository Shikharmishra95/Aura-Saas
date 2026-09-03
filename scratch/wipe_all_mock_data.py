import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.session import async_session_factory
from sqlalchemy import text

async def purge_database():
    async with async_session_factory() as session:
        print("🧹 Starting MySQL Database Purge (Preserving shiva9532 Platform Owner)...")
        
        # Disable foreign key checks for clean truncation/deletion
        await session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        
        # 1. Truncate mock data tables
        tables_to_truncate = [
            "appointments",
            "medical_records",
            "leaves",
            "doctors",
            "hospital_settings",
            "departments",
            "hospitals"
        ]
        
        for table in tables_to_truncate:
            try:
                await session.execute(text(f"TRUNCATE TABLE `{table}`;"))
                print(f"  ✓ Cleared table `{table}`")
            except Exception as e:
                print(f"  ⚠️ Truncate error on `{table}`: {e}")
                
        # 2. Delete non-owner users and their user_roles
        await session.execute(text("DELETE FROM user_roles WHERE user_id != 'shiva9532';"))
        await session.execute(text("DELETE FROM users WHERE username != 'shiva9532';"))
        print("  ✓ Cleared all non-owner user accounts & user_roles")

        # 3. Re-enable foreign key checks
        await session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        await session.commit()
        print("🎉 Database successfully purged! 0 mock hospitals remaining.")

if __name__ == "__main__":
    asyncio.run(purge_database())
