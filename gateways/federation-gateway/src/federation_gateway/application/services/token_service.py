"""
Token service for JWT operations
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException

from settings.settings_manager import SettingsManager


class TokenService:
    """Service for JWT token operations."""
    
    def __init__(self, settings: SettingsManager):
        self.settings = settings
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.settings.token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "iss": "federation-gateway"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm)
        return encoded_jwt
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(
                token, 
                self.settings.jwt_secret, 
                algorithms=[self.settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def extract_token_from_header(self, auth_header: Optional[str]) -> str:
        """Extract token from Authorization header."""
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        return auth_header.split(" ")[1]