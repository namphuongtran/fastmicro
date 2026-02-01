"""
Domain entities for authentication
"""

from pydantic import BaseModel


class UserInfo(BaseModel):
    sub: str
    name: str | None = None
    email: str | None = None
    preferred_username: str | None = None
    roles: list[str] | None = None
