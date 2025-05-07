from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class EducationItem(BaseModel):
    degree: str
    institution: str
    field_of_study: Optional[str] = None
    start_year: int
    end_year: Optional[int] = None
    description: Optional[str] = None


class ExperienceItem(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    current: bool = False
    description: Optional[str] = None


class SkillItem(BaseModel):
    name: str
    proficiency: str  # beginner, intermediate, advanced, expert
    years_of_experience: Optional[int] = None


class JobPreference(BaseModel):
    job_title: str
    location: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None  # full-time, part-time, contract, etc.


class UserProfileBase(BaseModel):
    # full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(UserProfileBase):
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
    resume_url: Optional[str] = None
    resume_original_filename: Optional[str] = None
    preferred_job_titles: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    preferred_salary: Optional[str] = None
    job_type_preferences: Optional[List[str]] = None
    is_profile_public: bool
    is_resume_public: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserProfilePublic(UserProfileInDB):
    pass


class ResumeUploadResponse(BaseModel):
    message: str
    resume_url: Optional[str] = None
    filename: Optional[str] = None