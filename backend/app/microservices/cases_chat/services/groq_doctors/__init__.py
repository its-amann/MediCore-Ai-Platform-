"""
Groq AI Doctors Service
Implements three specialized doctors using Groq API
"""

from .doctor_service import DoctorService
from .doctor_profiles import DOCTOR_PROFILES

__all__ = ["DoctorService", "DOCTOR_PROFILES"]