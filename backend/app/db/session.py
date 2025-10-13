"""
Database session management
"""
from contextlib import contextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=True,
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create synchronous engine for Celery tasks
sync_engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Create synchronous session factory for Celery tasks
SyncSessionLocal = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


@contextmanager
def get_db_context():
    """
    Context manager for synchronous database session (for Celery tasks)

    Usage:
        with get_db_context() as db:
            result = db.execute(select(User).where(User.id == 1))
            user = result.scalar_one_or_none()
    """
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


async def get_db() -> AsyncSession:
    """
    Dependency for getting async database session

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
