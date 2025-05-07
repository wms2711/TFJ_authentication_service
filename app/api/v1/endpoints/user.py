"""
User Management Router
=====================

Handles all user-related endpoints including:
- User registration
- Current user profile retrieval
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.user import UserInDB
from app.services.auth import AuthService
from app.services.user import UserService, UserCreate
from app.dependencies import get_current_user

# Initialize router with prefix and tags for OpenAPI documentation
router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserInDB)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    
    Flow:
    1. Receives user registration data
    2. Validates uniqueness of username/email
    3. Hashes password
    4. Creates user record in database
    
    Args:
        user: User creation data (username, email, password, etc.)
        db: Active database session
        
    Returns:
        UserInDB: Created user information (excluding password)
        
    Raises:
        HTTPException: 400 if username/email already exists
    """

    # Initialize user service with database session
    user_service = UserService(db)
    return user_service.create_user(user)

@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    """
    Get current authenticated user's profile
    
    Flow:
    1. Validates JWT from Authorization header
    2. Retrieves current user from database
    3. Returns user profile
    
    Args:
        current_user: Automatically injected from JWT
        
    Returns:
        UserInDB: Authenticated user's profile
    """
    return current_user

# To implement:
# - PATCH /users/me to update own profile
# - DELETE /users/me to self-delete profile