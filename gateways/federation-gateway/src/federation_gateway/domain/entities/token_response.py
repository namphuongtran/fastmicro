"""
Domain entities for authentication
"""

from pydantic import BaseModel
from typing import Optional

class TokenResponse(BaseModel):
    access_token: str
    id_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int