"""
Domain entities for authentication
"""


from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    id_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int
