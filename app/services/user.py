"""
User Management Service
======================

Handles all business logic related to user account operations:
- User registration
- User data retrieval
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.database.models.user import User
from app.schemas.user import UserCreate, UserInDB
from app.services.auth import AuthService

class UserService:
    """Main user service handling account management."""

    def __init__(self, db: Session):
        """
        Initialize with database session.
        
        Args:
            db: SQLAlchemy session for database operations
        """
        self.db = db

    def create_user(self, user: UserCreate) -> User:
        """
        Register a new user account.
        
        Flow:
        1. Checks username availability
        2. Hashes password
        3. Creates user record
        4. Commits to database
        
        Args:
            user: UserCreate schema with registration data
            
        Returns:
            User: Created SQLAlchemy user model
            
        Raises:
            HTTPException: 400 if username already exists
        """
        # Check for existing user
        db_user = self.db.query(User).filter(User.username == user.username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Hash password before storage
        hashed_password = AuthService(self.db).get_password_hash(user.password)
        
        # Create new user record
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            full_name=user.full_name
        )

        # Persist to database
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_user(self, user_id: int) -> User | None:
        """
        Retrieve user by primary key ID.
        
        Args:
            user_id: Database ID of user
            
        Returns:
            User: If user found
            None: If user doesn't exist
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> User | None:
        """
        Retrieve user by unique username.
        
        Args:
            username: Exact username to search
            
        Returns:
            User: If user found
            None: If user doesn't exist
        """
        return self.db.query(User).filter(User.username == username).first()