"""
Database connection and session management with async support.
Uses asyncpg for high-performance async PostgreSQL operations.
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
import logging

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/ethera")

# Convert to async PostgreSQL URL
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine with connection pooling
engine_options = {"echo": False, "pool_pre_ping": True}
if not ASYNC_DATABASE_URL.startswith("sqlite"):
    engine_options.update(pool_size=20, max_overflow=10, pool_recycle=3600)
engine = create_async_engine(ASYNC_DATABASE_URL, **engine_options)

read_url = os.getenv("READ_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
read_engine = create_async_engine(read_url, **engine_options) if read_url else engine

# Async session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)
ReadSessionLocal = sessionmaker(read_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)

# Base class for models
Base = declarative_base()

async def get_db():
    """Dependency for FastAPI to inject async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_read_db():
    """Route read-only endpoints to a replica when READ_DATABASE_URL is configured."""
    async with ReadSessionLocal() as session:
        yield session

async def init_db():
    """Verify database connectivity; schema changes are managed by Alembic."""
    async with engine.connect() as conn:
        await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
