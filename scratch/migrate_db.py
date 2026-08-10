import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('mysql+aiomysql://root:ZvNIsPJkPHVgYApdcNoIUPxXHrTMmSKL@tokaido.proxy.rlwy.net:11118/railway')
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE appointments ADD COLUMN payment_status VARCHAR(50) DEFAULT 'PENDING'"))
            print("Added payment_status")
        except Exception as e:
            print("payment_status error:", e)
            
        try:
            await conn.execute(text("ALTER TABLE appointments ADD COLUMN consultation_status VARCHAR(50) DEFAULT 'PENDING'"))
            print("Added consultation_status")
        except Exception as e:
            print("consultation_status error:", e)
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
