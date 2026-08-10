import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.database.declarative import Base
from app.database.models.appointment import * # Ensure all models are loaded

async def main():
    engine = create_async_engine('mysql+aiomysql://root:ZvNIsPJkPHVgYApdcNoIUPxXHrTMmSKL@tokaido.proxy.rlwy.net:11118/railway')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("All missing tables created successfully!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
