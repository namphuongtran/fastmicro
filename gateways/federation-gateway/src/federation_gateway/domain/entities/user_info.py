"""
Domain entities for authentication
"""

from pydantic import BaseModel
from typing import Optional, List


class UserInfo(BaseModel):
    sub: str
    name: Optional[str] = None
    email: Optional[str] = None
    preferred_username: Optional[str] = None
    roles: Optional[List[str]] = None