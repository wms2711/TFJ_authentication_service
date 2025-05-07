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
from app.config import settings

# Creates the connection pool and manages physical DB connections
engine = create_engine(settings.DATABASE_URL)

# Configures the session maker that generates individual sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Generator function that yields database sessions.
    
    Usage:
    - Injected into FastAPI route handlers via Depends()
    - Automatically closes session after request completes
    
    Yields:
        Session: A new database session
    
    Example:
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()