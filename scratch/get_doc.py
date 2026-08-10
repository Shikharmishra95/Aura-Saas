import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('mysql+aiomysql://root:@localhost:3306/hospital_voice_db')
    async with engine.begin() as conn:
        doc = (await conn.execute(text('SELECT id FROM doctors LIMIT 1'))).fetchone()
        if doc:
            print(f"Doctor ID: {doc[0]}")
            
            # Execute the API logic basically by updating the DB directly, or I can just call the API using httpx.
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
