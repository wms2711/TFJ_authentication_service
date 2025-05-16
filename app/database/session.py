"""
Database Session Management
==========================

Configures SQLAlchemy database connections and session handling.
This module provides:
1. Database engine configuration
2. Session factory setup
3. Dependency-injected session generator
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.config import settings

# Creates the connection pool and manages physical DB connections
engine = create_engine(settings.DATABASE_URL)
async_engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,  # starts with postgresql+asyncpg://
    pool_pre_ping=True,
    echo=False,
    future=True
)

# Configures the session maker that generates individual sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

def get_db():
    """
    Generator function that yields database sessions.
    
    Usage:
    - Injected into FastAPI route handlers via Depends().
    - Automatically closes session after request completes.
    
    Yields:
        Session: A new database session.
    
    Example:
        def get_items(db: Session = Depends(get_db)):
            pass
    """
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def async_get_db():
    """
    Async generator function that yields asynchronous database sessions.
    
    Usage:
    - Injected into FastAPI route handlers via Depends().
    - Manages session lifecycle asynchronously:
        * Commits if the request completes successfully.
        * Rolls back on exceptions.
        * Ensures session is closed after usage.
    
    Yields:
        AsyncSession: A new asynchronous database session.
    
    Example:
        async def get_items(db: AsyncSession = Depends(async_get_db)):
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()