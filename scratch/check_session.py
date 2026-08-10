import asyncio
import sys
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        print("=== RECENT VOICE SESSIONS ===")
        r = await conn.execute(text(
            "SELECT id, session_status, current_state, booking_context, created_at "
            "FROM voice_sessions "
            "ORDER BY created_at DESC LIMIT 5"
        ))
        for row in r.fetchall():
            ctx_str = json.dumps(row[3], ensure_ascii=False) if row[3] else "None"
            print(f"ID: {row[0]}, Status: {row[1]}, State: {row[2]}, Context: {ctx_str}, CreatedAt: {row[4]}")
            
        print("\n=== RECENT CONVERSATION LOGS ===")
        r2 = await conn.execute(text(
            "SELECT speaker, transcript, created_at "
            "FROM conversation_logs "
            "ORDER BY created_at DESC LIMIT 10"
        ))
        for row in r2.fetchall():
            print(f"Speaker: {row[0]}, Transcript: {row[1]}, CreatedAt: {row[2]}")
            
    await engine.dispose()

asyncio.run(main())
