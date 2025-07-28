"""
Domain entities for authentication
"""

from pydantic import BaseModel
from typing import Optional


class UserInfo(BaseModel):
    """User information entity."""
    sub: str
    email: Optional[str] = None
    name: Optional[str] = None
    preferred_username: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None