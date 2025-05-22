"""
Email infrastructure package.
"""
from app.infrastructure.email.gmail_client import get_recent_emails

__all__ = ['get_recent_emails'] 