"""
Base service classes for Cases Chat microservice
"""
from .doctor_service_base import BaseDoctorService
from .storage_base import BaseStorage

__all__ = ["BaseDoctorService", "BaseStorage"]