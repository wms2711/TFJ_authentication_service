"""
Application Entry Point - Run Server
===================================

This script serves as the entry point to launch the FastAPI application using Uvicorn ASGI server.
"""

import uvicorn

if __name__ == "__main__":
    # Import path to the FastAPI application instance
    # "app.main" is the Python module path (app/main.py)
    # "app" is the FastAPI instance variable name
    # Bind to all available network interfaces (0.0.0.0)
    # Run on port 9000
    # Enable auto-reload during development and restart server during code changes
    uvicorn.run("app.main:app", host="0.0.0.0", port=9000, reload=True)