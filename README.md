# Purpose of this service
This service handles authentication (login), user information (storing information like personal info, professional info, education, work experience, skills, resume, job perference etc) and job application (swipe right send to redis pub/sub)

# Quick Start
## Installation (virtual environment) for Linux
```bash
python -m venv <your-env>
source <your-env>/bin/activate
```
## Run service
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

# Add User profile (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `POST` request to:
```bash
http://127.0.0.1:9000/profiles/me
```
Payload below as reference:
```bash
{
  "age": 29,
  "gender": "male",
  "phone_number": "12345678",
  "address": "123 singapore",
  "city": "Singapore",
  "country": "Singapore",
  "postal_code": "123456"
}
```
Example of the response:
```bash
{
    "age": 29,
    "gender": "male",
    "phone_number": "12345678",
    "address": "123 singapore",
    "city": "Singapore",
    "country": "Singapore",
    "postal_code": "123456",
    "id": 1,
    "user_id": 1,
    "headline": null,
    "summary": null,
    "current_position": null,
    "current_company": null,
    "years_of_experience": null,
    "education": null,
    "experience": null,
    "skills": null,
    "resume_url": null,
    "resume_original_filename": null,
    "preferred_job_titles": null,
    "preferred_locations": null,
    "preferred_salary": null,
    "job_type_preferences": null,
    "is_profile_public": true,
    "is_resume_public": true,
    "created_at": "2025-05-07T08:17:41.167078+07:00",
    "updated_at": "2025-05-07T08:17:41.167078+07:00"
}
```

# List User profile (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/profiles/me
```
Example of the response:
```bash
{
    "age": 29,
    "gender": "male",
    "phone_number": "12345678",
    "address": "123 singapore",
    "city": "Singapore",
    "country": "Singapore",
    "postal_code": "123456",
    "id": 1,
    "user_id": 1,
    "headline": null,
    "summary": null,
    "current_position": null,
    "current_company": null,
    "years_of_experience": null,
    "education": null,
    "experience": null,
    "skills": null,
    "resume_url": null,
    "resume_original_filename": null,
    "preferred_job_titles": null,
    "preferred_locations": null,
    "preferred_salary": null,
    "job_type_preferences": null,
    "is_profile_public": true,
    "is_resume_public": true,
    "created_at": "2025-05-07T08:17:41.167078+07:00",
    "updated_at": "2025-05-07T08:17:41.167078+07:00"
}
```

# Update User profile (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `PUT` request to:
```bash
http://127.0.0.1:9000/profiles/me
```
Payload below as reference:
```bash
{
  "age": 29,
  "gender": "male",
  "phone_number": "12345678",
  "address": "123 singapore",
  "city": "Singapore",
  "country": "Singapore",
  "postal_code": "123456",
  "headline": "Hello this is a new headline"
}
```
Example of the response:
```bash
{
    "age": 29,
    "gender": "male",
    "phone_number": "12345678",
    "address": "123 singapore",
    "city": "Singapore",
    "country": "Singapore",
    "postal_code": "123456",
    "id": 1,
    "user_id": 1,
    "headline": "Hello this is a new headline",
    "summary": null,
    "current_position": null,
    "current_company": null,
    "years_of_experience": null,
    "education": null,
    "experience": null,
    "skills": null,
    "resume_url": null,
    "resume_original_filename": null,
    "preferred_job_titles": null,
    "preferred_locations": null,
    "preferred_salary": null,
    "job_type_preferences": null,
    "is_profile_public": true,
    "is_resume_public": true,
    "created_at": "2025-05-07T08:17:41.167078+07:00",
    "updated_at": "2025-05-07T08:21:44.239568+07:00"
}
```

# Upload resume into User profile (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `POST` request to:
```bash
http://127.0.0.1:9000/profiles/me/resume
```
Payload choose `form-data`, choose `file` in key field and upload file at the value field below as reference
Example of the response:
```bash
{
    "message": "Resume uploaded successfully",
    "resume_url": "uploads/resumes/65b6b5d7-955a-484a-93f7-e1fb24866596.docx",
    "filename": "test_doc.docx"
}
```

# Delete resume (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `DELETE` request to:
```bash
http://127.0.0.1:9000/profiles/me/resume
```
Example of the response:
```bash
None or 204 No content
```

# Get resume or download resume (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/profiles/me/resume
```
Example of the response header:
```bash
content-type: application/octet-stream
content-disposition: attachment; filename="test_doc.docx"
content-length: 30 
```
Example of the response body (it will contain the contents of the file):
```bash
This is a test document
```

# Job application for the user (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `POST` request to:
```bash
http://127.0.0.1:9000/application/
```
Payload below as reference:
```bash
{
  "job_id": "abc123"
}
```

# Job application patching for the user (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `PATCH` request to:
```bash
http://127.0.0.1:9000/application/1
```
Payload below as reference:
```bash
{
  "status": "completed",
  "ml_status": "success"
}
```

# Project Structure
```authentication_service/
├── uploads/
│   └── resumes/
│        └── <store resumes as UUID>  # Store resume (to change this method)
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app setup
│   ├── config.py                     # App configuration
│   ├── dependencies.py               # App dependency injections
│   ├── database/
│   │   ├── __init__.py
│   │   ├── base.py                   # Base model
│   │   ├── session.py                # Database session management
│   │   └── models/
│   │       ├── enums/
│   │       │    ├── __init__.py
│   │       │    └── application.py   # Models enums for application
│   │       ├── user.py               # Database: User model
│   │       ├── profile.py            # Database: User profile model
│   │       └── application.py        # Database: Job application model
│   ├── schemas/                      # Pydantic models
│   │   ├── __init__.py
│   │   ├── user.py                   # User Data Schemas
│   │   ├── token.py                  # Authentication Token Schemas
│   │   ├── profile.py                # User Profile Data Schemas
│   │   └── application.py            # Job Application Data Schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py                   # Auth service
│   │   ├── user.py                   # User service
│   │   ├── profile.py                # User Profile service
│   │   ├── redis.py                  # Redis Pub/Sub + streams service
│   │   ├── application.py            # Jon application service
│   │   └── ml_client.py              # Mock ML service
│   └── api/
│       ├── __init__.py
│       ├── v1/
│           ├── __init__.py
│           └── endpoints/
│               ├── __init__.py
│               ├── auth.py           # Auth router
│               ├── profile.py        # Profile router
│               ├── user.py           # User router
│               └── applications.py   # Job Application router
├── requirements.txt
├── .env                              # Environment variables
├── run.py                            # Application entry point for dev
└── worker.py                         # Background redis pub/sub processing
```