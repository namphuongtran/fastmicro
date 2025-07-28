"""
Domain entities for authentication
"""

from pydantic import BaseModel
from typing import Optional

class TokenValidationResponse(BaseModel):
    """Token validation response entity."""
    valid: bool
    sub: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None