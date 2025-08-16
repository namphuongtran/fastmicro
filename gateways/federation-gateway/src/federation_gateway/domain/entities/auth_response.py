"""
Domain entities for authentication
"""

from pydantic import BaseModel

class AuthResponse(BaseModel):
    authorization_url: str
    state: str