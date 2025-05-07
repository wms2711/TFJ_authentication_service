# Run app
python3 run.py

# Add valid JWT for example
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.eyJjdXN0b206cGxhbiI6IlNUQU5EQVJEIiwiY3VzdG9tOnRlbmFudF9pZCI6IjIwOWY4OGUyLTQ2NTEtNDdhNy1iYzA3LWExZDNiOGM0ZWVmZCIsImlhdCI6MTczMjUxNzM5OCwibmFtZSI6Ik1pbmcgU2hlbiIsInJvbGUiOiJTdXBlckFkbWluIiwic3ViIjoiZjk5YTg1M2MtYzAxMS03MGVkLTI3MDktZmY4MTBkZWNjYjkxIn0.BYa41sdZRaYL0wlpTcqzCFv2zt5oeZcWXfNP29s28wJQ3YK6PFbm7_XUYUQ_Nn7DhMArNFR3k8xc7iwYKMTr7VmEqHelyHhBsvMAGJiZVvUWSl8j9IT328ICRtWa7Cag8oQlnik6kRH6sCM4Qc0DoK0tz4L8Mg-3HcMuNfz0ATcytrxR1am8-3GkbG9YE3jkQgP5H-obfFGyZm-Q5RHhh52cpgrQ-vYlYTUXR75l7zFVrbCR4-kAdhDPrLL90JU2VyDOGn8ZAK1sJ1HukL7de4x7CC6Q7WJOe301JQXD2g1Mm4Rc5JQKDpVUQN8y8OR7R84LCXxKAyXkMtnUeFF9cQ

# Test service is up
## Request
GET: http://127.0.0.1:9000/

# Create user
## Request
POST: http://127.0.0.1:9000/users/
## Payload
{
  "username": "wms27111",
  "email": "wangmingshen2@gmail.com",
  "full_name": "Wang Ming Shen",
  "password": "abcd1234"
}

# Login
## Request
POST: http://127.0.0.1:9000/auth/login
## Payload choose "form-data" in body field
username: wms2711
password: abcd1234

# Get user's profile (to test this, you should /auth/login first and input the response from login into Header "Authorization")
## Request
GET: http://127.0.0.1:9000/users/me
## Payload (optional)
{
  "username": "wms2711",
  "email": "wangmingshen1@gmail.com",
  "full_name": "Wang Ming Shen",
  "id": 1,
  "is_active": false
}

# Refresh token (to test this, you should /auth/login first and input the response from login into Header "Authorization")
## Request
POST http://127.0.0.1:9000/auth/refresh-token
## Response example
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ3bXMyNzExIiwiZXhwIjoxNzQ2NTgxMTU4fQ.xdBuX1bNfMLtlT7zLOeOcoXPUacPS7wN5NreDcZs2o4",
    "token_type": "bearer"
}

# Check token (to test this, you should /auth/login first and input the response from login into Header "Authorization")
## Request
GET http://127.0.0.1:9000/auth/check-token
## Response example
{
    "valid": true,
    "user": "wms2711"
}

# Map
authentication_service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app setup
│   ├── config.py            # App configuration
│   ├── dependencies.py      # App dependency injections
│   ├── database/
│   │   ├── __init__.py
│   │   ├── base.py          # Base model
│   │   ├── session.py       # Database session management
│   │   └── models/
│   │       └── user.py      # Database: User model
│   ├── schemas/             # Pydantic models
│   │   ├── __init__.py
│   │   ├── user.py          # User Data Schemas
│   │   └── token.py         # Authentication Token Schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py          # Auth service
│   │   └── user.py          # User service
│   └── api/
│       ├── __init__.py
│       ├── v1/
│           ├── __init__.py
│           ├── endpoints/
│               ├── __init__.py
│               ├── auth.py  # Auth router
│               └── user.py  # User router
├── requirements.txt
├── .env                     # Environment variables
└── run.py                   # Application entry point for dev