"""
Domain entities for authentication
"""

from pydantic import BaseModel
from typing import Optional

class AuthenticationResult(BaseModel):
    """Authentication result entity."""
    success: bool
    access_token: Optional[str] = None
    error: Optional[str] = None
    error_description: Optional[str] = None