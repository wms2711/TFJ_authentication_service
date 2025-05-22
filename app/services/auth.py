"""
Authentication Service
=====================

Core service handling all authentication-related operations:
- Password hashing/verification
- JWT token generation/validation
- User authentication
"""

from datetime import datetime, timedelta
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.database.session import get_db, async_get_db
from app.database.models.user import User
from app.schemas.token import TokenData
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
import logging
from app.schemas.user import UserInDB
import uuid
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Password hashing configuration using bcrypt algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 token bearer scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class AuthService:
    """Main authentication service handling security operations."""

    def __init__(
            self, 
            db: AsyncSession = Depends(async_get_db)
        ):
        """
        Initialize with database session.
        
        Args:
            db (AsyncSession): SQLAlchemy async database session.
        """
        self.db = db

    def verify_password(
            self, 
            plain_password: str, 
            hashed_password: str
        ) -> bool:
        """
        Verify a plain password against its hashed version.
        
        Args:
            plain_password (str): User-supplied password.
            hashed_password (str): Stored password hash.
            
        Returns:
            bool: True if password matches hash.
        """
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error("Password verification failed", exc_info=True)
            return False

    def get_password_hash(
            self, 
            password: str
        ) -> str:
        """
        Generate secure password hash.
        
        Args:
            password (str): Plain text password.
            
        Returns:
            str: Hashed password.
        """
        return pwd_context.hash(password)

    async def get_user(
            self, 
            username: str
        ) -> User:
        """
        Retrieve user by username to query database.
        
        Args:
            username (str): Unique username identifier.
            
        Returns:
            User: SQLAlchemy User model if found.

        Raises:
            HTTPException: 
                - 404 if user not found.
                - 500 if a database error occurs.
        """
        try:
            stmt = select(User).where(User.username == username)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"User not found with email: {user}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with username '{username}' not found"
                )
            return user
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error fetching user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user information"
            )
    
    async def get_user_by_email(
            self, 
            email: str
        ) -> User:
        """
        Retrieve user by email to query database.
        
        Args:
            email (str): Unique email identifier.
            
        Returns:
            User: SQLAlchemy User model if found.
            
        Raises:
            HTTPException: 
                - 404 if user not found.
                - 500 if a database error occurs.
        """
        try:
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            email = result.scalar_one_or_none()

            if not email:
                logger.warning(f"User not found with email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with email '{email}' not found"
                )
            return email
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error fetching user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user information"
            )

    async def authenticate_user(
            self, 
            username: str, 
            password: str
        ) -> User:
        """
        Authenticate user credentials.
        
        Args:
            username (str): Account username.
            password (str): Plain text password.
            
        Returns:
            User: The authenticated user object.

        Raises:
            HTTPException: 401 Unauthorized if authentication fails.
            HTTPException: 500 Internal Server Error on unexpected failure.
        """
        try:
            user = await self.get_user(username)
            if not user or not self.verify_password(password, user.hashed_password):
                logger.warning(f"Failed login attempt for username: {username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )
            logger.info(f"User authenticated: {username}")
            return user
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during authentication for {username}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )


    def create_access_token(
            self, 
            data: dict, 
            expires_delta: Optional[timedelta] = None
        ) -> str:
        """
        Generate JWT access token.
        
        Args:
            data (dict): Payload to encode (should contain 'sub' claim).
            expires_delta (Optional[timedelta]): Optional token lifetime.
            
        Returns:
            str: Encoded JWT token.

        Raises:
            RuntimeError: If token creation fails due to encoding error.
        """
        try:
            to_encode = data.copy()
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=15)
            to_encode.update({"exp": expire})
            encoded_jwt = jwt.encode(
                to_encode, 
                settings.SECRET_KEY, 
                algorithm=settings.ALGORITHM
            )
            return encoded_jwt
        except JWTError as e:
            logger.error("JWT encoding error", exc_info=True)
            raise RuntimeError("Failed to generate access token") from e
    
    def create_reset_token(
            self, 
            email: str, 
            expires_delta: Optional[timedelta] = None
        ) -> str:
        """
        Generate a one-time-use JWT token for password reset.
        
        Args:
            email (str): User's email address to associate with the token.
            expires_delta (timedelta | None): Optional token lifetime. 
                Defaults to 15 minutes if not specified.
                
        Returns:
            str: Encoded JWT token containing:
                - sub: User's email (subject claim).
                - exp: Expiration timestamp.
                - jti: Unique token identifier (for one-time use tracking).
                - purpose: "password_reset".
                
        Raises:
            RuntimeError: If JWT encoding fails.
        """
        try:
            to_encode = {
                "sub": email,
                "jti": str(uuid.uuid4()),  # Unique token ID for one-time use tracking
                "purpose": "password_reset"  # Explicit token purpose
            }
        
            # Set expiration (default 15 minutes if not specified)
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=15)
        
            to_encode.update({"exp": expire})
            token = jwt.encode(
                to_encode,
                settings.SECRET_KEY,
                algorithm=settings.ALGORITHM
            )
            return token
        except JWTError as e:
            logger.error("JWT reset token encoding failed", exc_info=True)
            raise RuntimeError("Failed to generate reset token") from e

    async def get_current_user(
            self, 
            token: str = Depends(oauth2_scheme)
        ) -> User:
        """
        Validate JWT and return corresponding user.
        
        Args:
            token (str): JWT from Authorization header.
            
        Returns:
            User: Authenticated user.
            
        Raises:
            HTTPException: 401 if token is invalid.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            username: str = payload.get("sub")
            if not username:
                logger.warning("JWT missing 'sub' claim")
                raise credentials_exception
            token_data = TokenData(username=username)
        except JWTError as e:
            logger.error(f"JWT validation failed: {str(e)}", exc_info=True)
            raise credentials_exception
        
        user = await self.get_user(username=token_data.username)
        if not user:
            logger.warning(f"Token valid but user not found: {username}")
            raise credentials_exception
        return user
    
    async def get_current_active_user(
            self, 
            token: str = Depends(oauth2_scheme)
        ) -> UserInDB:
        """
        Get currently authenticated user (active only).
        
        Args:
            token (str): JWT from Authorization header.
            
        Returns:
            UserInDB: Pydantic model of authenticated user.
            
        Raises:
            HTTPException: 400 if user inactive.
        """
        user = await self.get_current_user(token)
        if not user.is_active:
            logger.warning(f"Inactive user access attempt: {user.username}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account")
        return UserInDB.model_validate(user)
    
    def verify_reset_token(
            self, 
            token: str
        ) -> str | None:
        """ 
        Decode and validate a password reset token.

        Args:
            token (str): JWT token received from password reset link.

        Returns:
            str: Email address if token is valid and purpose is 'password_reset'.
            None: If token is invalid, expired, or has wrong purpose.
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            purpose: str = payload.get("purpose")
            
            if not email or purpose != "password_reset":
                logger.warning("Invalid reset token purpose or missing subject ('purpose' field in token).")
                return None
            
            return email
        
        except ExpiredSignatureError:
            logger.warning("Password reset token expired.")
        except JWTError as e:
            logger.error(f"Invalid JWT during reset verification: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error verifying reset token: {e}")

        return None

        
    def verify_email_token(
            self, 
            token: str
        ) -> str | None:
        """
        Verify email verification token and return email if valid.
        
        Args:
            token (str): JWT verification token
            
        Returns:
            str | None: Email address if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            purpose: str = payload.get("purpose")
            
            if not email or purpose != "email_verification":
                logger.warning("Invalid email verification token: missing subject or wrong purpose.")
                return None
            
            return email
        
        except ExpiredSignatureError:
            logger.warning("Email verification token expired.")
        except JWTError as e:
            logger.error(f"JWT error during email token verification: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error verifying email token: {e}")

        return None
        
    def generate_verification_token(
            self, 
            email: str
        ) -> str:
        """
        Generate a JWT token for email verification.
        
        Args:
            email (str): User's email address to verify.
            
        Returns:
            str: Encoded JWT token containing:
                - sub: User's email.
                - exp: Expiration timestamp (24 hours).
                - jti: Unique token ID.
                - purpose: "email_verification".
        """
        try:
            expire = datetime.utcnow() + timedelta(hours=24)  # 24 hours expiry
            to_encode = {
                "sub": email,
                "jti": str(uuid.uuid4()),
                "purpose": "email_verification"  # Explicit token purpose
            }
            to_encode.update({"exp": expire})
            token = jwt.encode(
                to_encode, 
                settings.SECRET_KEY, 
                algorithm=settings.ALGORITHM
            )
            return token
        except Exception as e:
            logger.exception(f"Failed to generate verification token for {email}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate email verification token"
            )
