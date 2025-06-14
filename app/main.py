from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.database.base import Base
from app.database.session import engine
from app.api.v1.endpoints import auth, user, profile, applications, job, admin, notification, chat

# Models for database creation
from app.database.models.user import User as UserDB
from app.database.models.profile import UserProfile as UserProfileDB
from app.database.models.application import Application as ApplicationDB
from app.database.models.job import Job as JobDB
from app.database.models.notification import Notification as NotificationDB
from app.database.models.report import ReportStatus as ReportStatusDB
from app.database.models.chat import ChatMessage as ChatMessageDB

# Initialize the FastAPI application
# --------------------------------
# This creates the core FastAPI instance that will handle all incoming requests
# and route them to the appropriate endpoints.
app = FastAPI(
    title="Authentication Service",
    description="API for user authentication and management",
    version="1.0.0"
)

# Configure rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Exception handler for rate limit errors
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Try again later."}
    )

# Add CORS middleware (adjust for security in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Table Creation
# ----------------------
# Creates all database tables defined in your SQLAlchemy models.
# This runs only once when the application starts up.
Base.metadata.create_all(bind=engine)

# Router Registration
# ------------------
# Includes the endpoint routers from different modules:
# - auth.router: Contains authentication-related endpoints (/login, /refresh-token, /check-token)
# - user.router: Contains user management endpoints (/users, /users/me)
# - profile.router: Contains profile management endpoints (/profiles/me, /profiles/me/resume)
# - applications.router: Contains application management when user apply or swipe right for jobs (/application)
# - job.router: Contains job management when job poster post job, update jobs, condidate fetch jobs
# - admin.router: Containes admin management getting all users and activate or deactivate users
# - notification.router: Contains notification management like creation, updating and listing
# - chat.router: Contains chat management like list all chats, list specific chat, websocket connection
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(profile.router)
app.include_router(applications.router)
app.include_router(job.router)
app.include_router(admin.router)
app.include_router(notification.router)
app.include_router(chat.router)

# Root Endpoint
# -------------
# A simple health check endpoint that:
# - Verifies the service is running
@app.get("/")
def read_root():
    return {"message": "Authentication Service running on port 9000"}