# Purpose of this service
This service handles authentication (login), user information (storing information like personal info, professional info, education, work experience, skills, resume, job perference etc) and job application (swipe right send to redis pub/sub)

# Quick Start
## Installation (virtual environment) for Linux
```bash
python -m venv <your-env>
source <your-env>/bin/activate
```
## Run service (dev: run both concurrently)
### Main app
```bash
python3 run.py
```
### Redis worker (process stream)
```bash
python3 worker.py
```

# Version History
### V1.0.0
- Auth and user credentials (login) service
###### V1.0.1
- Forget password - Initiate password reset by sending an link to user's email (with temporary token), by clicking the link in the email, user will be prompt to reset password 
###### V1.0.2
- Reset password - Verifies the temporary token and updates the password into database

### V1.1.0
- Added user profile / information service
###### V1.1.1
- User verification for new sign-ups - an email (with temporary token) will be sent to verify, user will be added to database at the meantime (as a non-verified user)
###### V1.1.2
- User update credentials - user can self-update credentials
###### V1.1.3
- User self-delete credentials - user can self-delete account, this will delete user_profile that is likned to user.id

### V1.2.0
- Added job application service
###### V1.2.1
- Replaced database session with async session  
  _Reason: To support non-blocking I/O and able to scale_
  
- Replaced CRUD operations with async equivalents  
  _Reason: Align with async DB session for full async request handling._

- Redis service remains synchronous  
  _Reason: Our implementation is fire-and-forget (no need to await replies), so async overhead is unnecessary._
###### V1.2.2
- Fetch status of application according to application id
###### V1.2.5
- Handle likes (swipe left) and dislikes (swipe left)

### V1.3.0
- Added redis service

### V1.4.0
- Added job service
###### V1.4.1
- Create jobs - only employers or admins can create jobs
###### V1.4.2
- Update jobs - only (employers | admins) & job creator can update jobs
###### V1.4.3
- Fetch single job detail - if job is expired or not active, only admin or job creator can fetch the job
###### V1.4.4
- Fetch all found filtered job detail - if job is expired or not active, only admin can fetch the job (upcoming update job creator can fetch also)
###### V1.4.5
- User report jobs

### V1.5.0
- Added admin service
###### V1.5.1
- Retrieving all users - only admins can do so
###### V1.5.2
- Updating user status (is_active, is_admin, is_employer) - only admins can modify, admin cannot modify itself or other admins

### V1.6.0
- Added notification service
###### V1.6.1
- Create notification - only admins and employers can do so (to add send mobile notification)
###### V1.6.2
- Create notification - users fetch notifications with cache
###### V1.6.3
- Mark as read - users read notification
###### V1.6.5
- Email formatting using Jinja

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
  "postal_code": "123456",
  "summary": "test",
  "education": [
    {
        "institution": "ABC Primary School",
        "degree": "Primary Certificate",
        "start_year": 2005
    }
    ]
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
    "id": 12,
    "user_id": 7,
    "headline": null,
    "summary": "test",
    "current_position": null,
    "current_company": null,
    "years_of_experience": null,
    "education": [
        {
            "degree": "Primary Certificate",
            "institution": "ABC Primary School",
            "start_year": 2005
        }
    ],
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
    "created_at": "2025-05-22T20:31:03.610705Z",
    "updated_at": "2025-05-22T20:31:03.610705Z"
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
    "resume_id": "7b7b31b1-a409-4692-a835-2499eeddce26",
    "filename": "test_doc.docx",
    "url": "uploads/resumes/1/20250602_060354_57dbae3048ab4d0aae5694eda70575ef.docx",
    "is_current": true,
    "uploaded_at": "2025-06-02T06:03:54.133088"
}
```

# Delete resume (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `DELETE` request to:
```bash
http://127.0.0.1:9000/profiles/me/resume/25269895-7157-4498-87c1-8c860127fba4
```
Example of the response:
```bash
None or 204 No content
```

# User retrieve all resumes that he/she has (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/profiles/me/resumes
```
Example of the response:
```bash
[
    {
        "id": "7b7b31b1-a409-4692-a835-2499eeddce26",
        "filename": "test_doc.docx",
        "url": "uploads/resumes/1/20250602_060354_57dbae3048ab4d0aae5694eda70575ef.docx",
        "is_current": false,
        "uploaded_at": "2025-06-02T06:03:54.133088"
    },
    {
        "id": "25269895-7157-4498-87c1-8c860127fba4",
        "filename": "test_doc.docx",
        "url": "uploads/resumes/1/20250602_063504_5723dabc0237438698b146d50ef5f624.docx",
        "is_current": true,
        "uploaded_at": "2025-06-02T06:35:04.744976"
    }
]
```

# User set this resume as the one he wants to use for applying jobs (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `PATCH` request to:
```bash
http://127.0.0.1:9000/profiles/me/resumes/25269895-7157-4498-87c1-8c860127fba4/set-current
```
Example of the response:
```bash
{
    "id": "25269895-7157-4498-87c1-8c860127fba4",
    "filename": "test_doc.docx",
    "url": "uploads/resumes/1/20250602_063504_5723dabc0237438698b146d50ef5f624.docx",
    "is_current": true,
    "uploaded_at": "2025-06-02T06:35:04.744976"
}
```

# Get resume or download resume (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/profiles/me/resume/25269895-7157-4498-87c1-8c860127fba4
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
  "job_id": "b108cf6d-eb01-45cc-9dbc-e61e92efcd23",
  "swipe_action": "dislike"  # or like
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

# Get job application details (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/application/1
```
Example of the response body:
```bash
{
    "job_id": "abc4",
    "id": 11,
    "user_id": 1,
    "status": "completed",
    "ml_status": "success",
    "created_at": "2025-05-16T06:22:09.654218",
    "updated_at": "2025-05-16T06:32:01.880980"
}
```

# User credentails patching (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `PATCH` request to:
```bash
http://127.0.0.1:9000/users/me
```
Payload below as reference:
```bash
{
  "email": "wangmingshen2@gmail.com",
  "username": <str>,
  "full_name": <str>,
  "is_active": <bool>,
}
```

# User credentails delete (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `DELETE` request to:
```bash
http://127.0.0.1:9000/users/me
```
Example of the response:
```bash
None or 204 No content
```

# User forget password
Send a `POST` request to:
```bash
http://127.0.0.1:9000/auth/forgot-password
```
Payload below as reference:
```bash
{
    "email": "wangmingshen1@gmail.com"
}
```
Example of the response body:
```bash
{
    "message": "Password reset link sent to your email"
}
```

# User reset password
Send a `POST` request to:
```bash
http://127.0.0.1:9000/auth/reset-password
```
Payload below as reference:
```bash
{
    "token": "eyJhb...",   # From the email generated from /auth/forgot-password
    "new_password": "111"
}
```

# Employers and admins post jobs (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `POST` request to:
```bash
http://127.0.0.1:9000/job/
```
Payload below as reference:
```bash
{
  "title": "Software Engineer"
}
```

# Employers and admins update jobs (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `PATCH` request to:
```bash
http://127.0.0.1:9000/job/b108cf6d-eb01-45cc-9dbc-e61e92efcd23
```
Payload below as reference:
```bash
{
  "title": "Software Engineer",
  "description": "Software Engineer for ...",
  "company_name": "company"
}
```

# Fetch single job (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/job/b108cf6d-eb01-45cc-9dbc-e61e92efcd23
```
Example of the response:
```bash
{
    "title": "Software Engineer",
    "description": "Software Engineer for ...",
    "company_name": "company",
    "contact_email": null,
    "location": null,
    "category": null,
    "remote_available": false,
    "salary_min": null,
    "salary_max": null,
    "currency": "SGD",
    "job_type": null,
    "experience_level": null,
    "skills_required": [],
    "language": [],
    "apply_url": null,
    "id": "b108cf6d-eb01-45cc-9dbc-e61e92efcd23",
    "is_active": true,
    "posted_at": "2025-05-26T01:34:24.626434",
    "expires_at": "2025-06-25T01:36:10.455000"
}
```

# Fetch all job (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/job/
```
Params below as reference:
```bash
{
  "remote": false,
  "title": "Software Engineer"
}
```
Example of the response:
```bash
{
    "meta": {
        "page": 1,
        "page_size": 20,
        "total": 3,
        "total_pages": 1
    },
    "results": [
        {
            "title": "Software Engineer",
            "description": null,
            "company_name": null,
            "contact_email": null,
            "location": null,
            "category": null,
            "remote_available": false,
            "salary_min": null,
            "salary_max": null,
            "currency": "SGD",
            "job_type": null,
            "experience_level": null,
            "skills_required": [],
            "language": [],
            "apply_url": null,
            "id": "e6741fad-d206-467d-9b81-00c28d46ab5f",
            "is_active": true,
            "posted_at": "2025-05-26T01:35:18.067504",
            "expires_at": "2025-06-25T01:35:18.067512"
        },
        {
            "title": "Software Engineer",
            "description": null,
            "company_name": null,
            "contact_email": null,
            "location": null,
            "category": null,
            "remote_available": false,
            "salary_min": null,
            "salary_max": null,
            "currency": "SGD",
            "job_type": null,
            "experience_level": null,
            "skills_required": [],
            "language": [],
            "apply_url": null,
            "id": "9d6b766d-a503-4c6d-8e61-3fa8912d9fad",
            "is_active": true,
            "posted_at": "2025-05-26T01:36:10.455491",
            "expires_at": "2025-06-25T01:35:18.067000"
        },
        {
            "title": "Software Engineer",
            "description": "Software Engineer for ...",
            "company_name": "company",
            "contact_email": null,
            "location": null,
            "category": null,
            "remote_available": false,
            "salary_min": null,
            "salary_max": null,
            "currency": "SGD",
            "job_type": null,
            "experience_level": null,
            "skills_required": [],
            "language": [],
            "apply_url": null,
            "id": "b108cf6d-eb01-45cc-9dbc-e61e92efcd23",
            "is_active": true,
            "posted_at": "2025-05-26T01:34:24.626434",
            "expires_at": "2025-06-25T01:35:18.067000"
        }
    ]
}
```

# Admins retrive all users (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/admin/users
```
Results below as reference:
```bash
[
    {
        "username": "wms2711",
        "email": "wangmingshen1@gmail.com",
        "full_name": "Wang Ming Shen",
        "id": 2,
        "is_active": true,
        "is_employer": true,
        "is_admin": false,
        "email_verified": false
    },
    {
        "username": "wms27111",
        "email": "mingshenliteon@gmail.com",
        "full_name": "Wang Ming Shen",
        "id": 1,
        "is_active": true,
        "is_employer": true,
        "is_admin": true,
        "email_verified": true
    }
]
```

# Admins patching user status (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/admin/users/2
```
Payload below as reference:
```bash
{
    "is_active": true,
    "is_admin": false,
    "is_employer": false
}
```

# Notification creation (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `POST` request to:
```bash
http://127.0.0.1:9000/notification/
```
Payload below as reference:
```bash
{
    "user_id": 2,
    "notification_title": "Application status updates",
    "message": "Your application was accepted"
}
```

# User read notifications (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `GET` request to:
```bash
http://127.0.0.1:9000/notification/
```
Response below as reference:
```bash
[
    {
        "user_id": 1,
        "notification_title": "Application status updates",
        "message": "Your application was accepted",
        "id": 5,
        "is_read": true
    },
    {
        "user_id": 1,
        "notification_title": "Application status updates",
        "message": "Your application was accepted",
        "id": 7,
        "is_read": true
    }
]
```

# Mark as read after user read notification (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `PATCH` request to:
```bash
http://127.0.0.1:9000/notification/{notification_id}
```
Response below as reference:
```bash
{
    "user_id": 1,
    "notification_title": "Application status updates",
    "message": "Your application was accepted",
    "id": 5,
    "is_read": true
}
```

# Report jobs (to test this, you should /auth/login first and input the response from login into Header "Authorization")
Send a `POST` request to:
```bash
http://127.0.0.1:9000/job/b108cf6d-eb01-45cc-9dbc-e61e92efcd23/report?reason=1
```
Response below as reference:
```bash
{
    "message":"Job reported successfully. Our team will review it shortly."
}
```
```bash
{
    "detail": "You have already reported this job"
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
│   │       │    ├── application.py   # Models enums for application
│   │       │    ├── job.py           # Job enums for job model
│   │       │    └── report.py        # Report enums for job report model
│   │       ├── user.py               # Database: User model
│   │       ├── profile.py            # Database: User profile model
│   │       ├── application.py        # Database: Job application model
│   │       ├── job.py                # Database: Jobs model
│   │       ├── notification.py       # Database: Notification model
│   │       └── report.py             # Database: Job report model
│   ├── schemas/                      # Pydantic models
│   │   ├── __init__.py
│   │   ├── user.py                   # User Data Schemas
│   │   ├── token.py                  # Authentication Token Schemas
│   │   ├── profile.py                # User Profile Data Schemas
│   │   ├── application.py            # Job Application Data Schemas
│   │   ├── job.py                    # Jobs Data Schemas
│   │   └── notification.py           # Notification Data Schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py                   # Auth service
│   │   ├── user.py                   # User service
│   │   ├── profile.py                # User Profile service
│   │   ├── redis.py                  # Redis Pub/Sub + streams service
│   │   ├── application.py            # Jon application service
│   │   ├── ml_client.py              # Mock ML service
│   │   ├── email.py                  # Email service
│   │   ├── job.py                    # Job service
│   │   ├── admin.py                  # Admin service
│   │   └── notification.py           # Notification service
│   ├── templates/
│   │   ├── notification_email.html   # Email template for notifications
│   │   ├── reset_password.html       # Email template for reset password
│   │   └── verify_email.html         # Email template for verify email
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           └── endpoints/
│               ├── __init__.py
│               ├── auth.py           # Auth router
│               ├── profile.py        # Profile router
│               ├── user.py           # User router
│               ├── applications.py   # Job Application router
│               ├── job.py            # Jobs router
│               ├── admin.py          # Admin router
│               └── notification.py   # Notification router
├── requirements.txt
├── .env                              # Environment variables
├── run.py                            # Application entry point for dev
└── worker.py                         # Background redis stream processing
```