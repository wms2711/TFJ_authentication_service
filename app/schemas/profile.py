"""
User Profile Data Schemas
=========================

Defines the data structures for user profile handling across different layers:
1. API request/response formats
2. Database model representations
3. Internal service transfers

Includes:
- Profile basics (age, contact, location)
- Education, experience, and skills
- Job preferences
- Resume metadata
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class EducationItem(BaseModel):
    """
    Represents a user's educational background.

    Fields:
        degree (str): Name of the degree or qualification.
        institution (str): Name of the educational institution.
        field_of_study (Optional[str]): Major or specialization.
        start_year (int): Start year of the education.
        end_year (Optional[int]): End year or expected graduation.
        description (Optional[str]): Additional details or achievements.
    """
    degree: str
    institution: str
    field_of_study: Optional[str] = None
    start_year: int
    end_year: Optional[int] = None
    description: Optional[str] = None


class ExperienceItem(BaseModel):
    """
    Represents a user's work experience entry.

    Fields:
        title (str): Job title or role.
        company (str): Employer or company name.
        location (Optional[str]): Geographic location.
        start_date (str): Start date in YYYY-MM format.
        end_date (Optional[str]): End date in YYYY-MM format, if not current.
        current (bool): True if this is the current position.
        description (Optional[str]): Description of duties and achievements.
    """
    title: str
    company: str
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    current: bool = False
    description: Optional[str] = None


class SkillItem(BaseModel):
    """
    Represents a specific skill with proficiency level.

    Fields:
        name (str): Name of the skill.
        proficiency (str): Skill level - possibly beginner, intermediate, advanced, expert etc.
        years_of_experience (Optional[int]): Number of years using the skill.
    """
    name: str
    proficiency: str
    years_of_experience: Optional[int] = None


class JobPreference(BaseModel):
    """
    Represents job preferences for recommendations or filtering.

    Fields:
        job_title (str): Desired job title.
        location (Optional[str]): Preferred job location.
        salary_range (Optional[str]): Expected salary range (e.g., "$3,000–$5,000").
        job_type (Optional[str]): Full-time, part-time, contract, etc.
    """
    job_title: str
    location: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None

class UserProfileBase(BaseModel):
    """
    Base user profile structure for shared fields.

    Includes:
    - Contact and demographic info
    - Address details
    """
    age: Optional[int] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None

    # class Config:
    #     extra = "forbid"  # Disallow unknown fields

class UserProfileCreate(UserProfileBase):
    """
    Schema for profile creation requests.

    Extends:
        UserProfileBase
    """
    headline: Optional[str] = None
    summary: Optional[str] = None
    current_position: Optional[str] = None
    current_company: Optional[str] = None
    years_of_experience: Optional[int] = None
    education: Optional[List[EducationItem]] = None
    experience: Optional[List[ExperienceItem]] = None
    skills: Optional[List[SkillItem]] = None
    preferred_job_titles: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    preferred_salary: Optional[str] = None
    job_type_preferences: Optional[List[str]] = None
    is_profile_public: Optional[bool] = None
    is_resume_public: Optional[bool] = None

    pass


class UserProfileUpdate(UserProfileBase):
    """
    Schema for profile update requests.

    Includes additional optional fields like:
    - Headline, summary
    - Current position details
    - Career-related lists (education, experience, skills)
    - Job preferences and visibility settings
    """
    headline: Optional[str] = None
    summary: Optional[str] = None
    current_position: Optional[str] = None
    current_company: Optional[str] = None
    years_of_experience: Optional[int] = None
    education: Optional[List[EducationItem]] = None
    experience: Optional[List[ExperienceItem]] = None
    skills: Optional[List[SkillItem]] = None
    preferred_job_titles: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    preferred_salary: Optional[str] = None
    job_type_preferences: Optional[List[str]] = None
    is_profile_public: Optional[bool] = None
    is_resume_public: Optional[bool] = None


class UserProfileInDB(UserProfileBase):
    """
    Full user profile stored in the database.

    Includes all fields from UserProfileUpdate, plus:
    - Resume metadata
    - Timestamps
    - Primary keys and identifiers

    orm_mode enables compatibility with SQLAlchemy models.
    """
    id: int
    user_id: int
    headline: Optional[str] = None
    summary: Optional[str] = None
    current_position: Optional[str] = None
    current_company: Optional[str] = None
    years_of_experience: Optional[int] = None
    education: Optional[List[Dict[str, Any]]] = None
    experience: Optional[List[Dict[str, Any]]] = None
    skills: Optional[List[Dict[str, Any]]] = None
    resumes: Optional[str] = None
    current_resume_id: Optional[str] = None
    preferred_job_titles: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    preferred_salary: Optional[str] = None
    job_type_preferences: Optional[List[str]] = None
    is_profile_public: bool
    is_resume_public: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfilePublic(UserProfileInDB):
    """
    Public version of the profile with all viewable fields.

    Inherits from:
        UserProfileInDB
    """
    pass