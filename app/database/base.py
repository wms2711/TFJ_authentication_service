"""
SQLAlchemy Base Model Declaration
================================

This module defines the foundational declarative base class for all database models.
It serves as the base class that all ORM models should inherit from.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create the declarative base class
Base = declarative_base()