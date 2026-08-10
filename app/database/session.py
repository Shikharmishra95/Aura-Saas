from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
from app.core.logging import db_logger

# 1. Async Database Engine and Session Factory (For FastAPI Operations)
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,  # Set to True for verbose SQLAlchemy queries logging in debugging
    pool_pre_ping=True,
    pool_recycle=120,         # Recycle connections every 2 minutes (Railway cloud DB)
    pool_size=10,             # Reduced pool size — Railway has connection limits
    max_overflow=20,          # Allow burst connections
    pool_timeout=30,          # Wait up to 30s for a pool slot before error
    connect_args={
        "connect_timeout": 30  # Max 30s to establish initial TCP connection
    }
)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# 2. Sync Database Engine (Specifically for Alembic migrations compatibility)
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    pool_pre_ping=True
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency yielding async session instances. Automatically rolls back on failure."""
    db_logger.debug("Creating new async database session.")
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
            db_logger.debug("Database session transaction committed.")
        except Exception as e:
            await session.rollback()
            db_logger.error(f"Database session transaction rolled back due to: {str(e)}")
            raise e
        finally:
            await session.close()
            db_logger.debug("Database session closed.")
