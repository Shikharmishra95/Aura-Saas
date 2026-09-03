import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from sqlalchemy import text
from app.database.session import async_session_factory

async def migrate_subscription_schema():
    async with async_session_factory() as db:
        print("Migrating MySQL 'hospitals' table for SaaS Subscriptions...")
        
        columns = [
            ("subscription_plan", "VARCHAR(50) DEFAULT 'STARTER'"),
            ("max_doctors", "INT DEFAULT 1"),
            ("ai_voice_enabled", "TINYINT(1) DEFAULT 0"),
            ("plan_status", "VARCHAR(20) DEFAULT 'ACTIVE'"),
            ("plan_expires_at", "DATETIME NULL")
        ]
        
        for col_name, col_def in columns:
            try:
                sql = f"ALTER TABLE hospitals ADD COLUMN {col_name} {col_def}"
                await db.execute(text(sql))
                print(f"✓ Added column: {col_name}")
            except Exception as e:
                if "Duplicate column name" in str(e) or "1060" in str(e):
                    print(f"ℹ Column {col_name} already exists.")
                else:
                    print(f"⚠ Warning on {col_name}: {str(e)}")
        
        # Set default values for existing hospitals (set hosp_default to ENTERPRISE for testing)
        await db.execute(text("UPDATE hospitals SET subscription_plan = 'ENTERPRISE', max_doctors = 999, ai_voice_enabled = 1 WHERE id = 'hosp_default'"))
        await db.commit()
        print("✅ Subscription Schema Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate_subscription_schema())
