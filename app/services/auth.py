"""
Authentication Service
=====================

Core service handling all authentication-related operations:
- Password hashing/verification
- JWT token generation/validation
- User authentication
"""

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.database.session import get_db
from app.database.models.user import User
from app.schemas.token import TokenData
from sqlalchemy.orm import Session
from app.config import settings
import logging
from app.schemas.user import UserInDB

# Configure logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Password hashing configuration using bcrypt algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 token bearer scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class AuthService:
    """Main authentication service handling security operations."""

    def __init__(self, db: Session = Depends(get_db)):
        """
        Initialize with database session.
        
        Args:
            db: SQLAlchemy session (injected via FastAPI Depends)
        """
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against its hashed version.
        
        Args:
            plain_password: User-supplied password
            hashed_password: Stored password hash
            
        Returns:
            bool: True if password matches hash
        """
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Generate secure password hash.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return pwd_context.hash(password)

    def get_user(self, username: str) -> User | None:
        """
        Retrieve user by username to query database.
        
        Args:
            username: Unique username identifier
            
        Returns:
            User: SQLAlchemy User model if found
            None: If user doesn't exist
        """
        return self.db.query(User).filter(User.username == username).first()

    def authenticate_user(self, username: str, password: str) -> User | None:
        """
        Authenticate user credentials.
        
        Args:
            username: Account username
            password: Plain text password
            
        Returns:
            User: If credentials are valid
            None: If authentication fails
        """
        user = self.get_user(username)
        if not user or not self.verify_password(password, user.hashed_password):
            log.warning(f"Failed login attempt for username: {username}")
            return None
        return user

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        """
        Generate JWT access token.
        
        Args:
            data: Payload to encode (should contain 'sub' claim)
            expires_delta: Optional token lifetime
            
        Returns:
            str: Encoded JWT token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        """
        Validate JWT and return corresponding user.
        
        Args:
            token: JWT from Authorization header
            
        Returns:
            User: Authenticated user
            
        Raises:
            HTTPException: 401 if token is invalid
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        except JWTError as e:
            log.error(f"JWT validation failed: {e}")
            raise credentials_exception
        
        user = self.get_user(username=token_data.username)
        if user is None:
            log.warning(f"Token valid but user not found: {username}")
            raise credentials_exception
        return user
    
    async def get_current_active_user(self, token: str = Depends(oauth2_scheme)) -> UserInDB:
        """
        Get currently authenticated user (active only).
        
        Args:
            token: JWT from Authorization header
            
        Returns:
            UserInDB: Pydantic model of authenticated user
            
        Raises:
            HTTPException: 400 if user inactive
        """
        user = self.get_current_user(token)
        if not user.is_active:
            log.warning(f"Inactive user access attempt: {user.username}")
            raise HTTPException(status_code=400, detail="Inactive user")
        return UserInDB.model_validate(user)