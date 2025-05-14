from fastapi import FastAPI
from app.database.base import Base
from app.database.session import engine
from app.api.v1.endpoints import auth, user, profile, applications

# Models for database creation
from app.database.models.user import User as UserDB
from app.database.models.profile import UserProfile as UserProfileDB
from app.database.models.application import Application as ApplicationDB

# Initialize the FastAPI application
# --------------------------------
# This creates the core FastAPI instance that will handle all incoming requests
# and route them to the appropriate endpoints.
app = FastAPI(
    title="Authentication Service",
    description="API for user authentication and management",
    version="1.0.0"
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
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(profile.router)
app.include_router(applications.router)

# To implement:
# - /admin endpoints for admin-only operations 
    # GET /admin/users to list all user
    # PATCH /admin/users/{id}/status for admin to deactivate or activate users

# Root Endpoint
# -------------
# A simple health check endpoint that:
# - Verifies the service is running
@app.get("/")
def read_root():
    return {"message": "Authentication Service running on port 9000"}