# Run app
```bash
python3 run.py
```

# Add valid header for Authorization example
| Key           | Value |
|---------------|-------|
| Authorization | `Bearer eyJhbGciOiJSUzI1NiJ...` |

# Test service is up
Send a `GET` request to:
```bash
http://127.0.0.1:9000/
```

# Create user
Send a `POST` request to:
```bash
http://127.0.0.1:9000/users/
```
Payload below as reference:
```bash
{
  "username": "wms27111",
  "email": "wangmingshen2@gmail.com",
  "full_name": "Wang Ming Shen",
  "password": "abcd1234"
}
```

# Login
Send a `POST` request to:
```bash
http://127.0.0.1:9000/auth/login
```
Payload choose `form-data` in body field, below as reference:
```bash
username: wms2711
password: abcd1234
```

# Get user's profile (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/users/me
```
Payload (optional) below as reference:
```bash
{
  "username": "wms2711",
  "email": "wangmingshen1@gmail.com",
  "full_name": "Wang Ming Shen",
  "id": 1,
  "is_active": false
}
```

# Refresh token (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `POST` request to:
```bash
http://127.0.0.1:9000/auth/refresh-token
```
Example of the response:
```bash
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ3bXMyNzExIiwiZXhwIjoxNzQ2NTgxMTU4fQ.xdBuX1bNfMLtlT7zLOeOcoXPUacPS7wN5NreDcZs2o4",
    "token_type": "bearer"
}
```

# Check token (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/auth/check-token
```
Example of the response:
```bash
{
    "valid": true,
    "user": "wms2711"
}
```

# Map
```authentication_service/
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
└── run.py                   # Application entry point for dev```