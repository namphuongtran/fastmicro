"""Password hashing and validation services.

This module provides secure password hashing using Argon2
and password strength validation.

Example:
    >>> from shared.auth.password import PasswordService, check_password_strength
    >>> service = PasswordService()
    >>> hashed = service.hash("SecureP@ssw0rd!")
    >>> service.verify("SecureP@ssw0rd!", hashed)
    True
    >>> check_password_strength("SecureP@ssw0rd!")
    True
"""

from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


class PasswordStrengthError(ValueError):
    """Raised when password does not meet strength requirements.
    
    This exception contains information about which requirements
    the password failed to meet.
    
    Attributes:
        message: Description of what requirements were not met.
        failed_requirements: List of requirement names that failed.
    """

    def __init__(
        self,
        message: str,
        failed_requirements: list[str] | None = None,
    ) -> None:
        """Initialize password strength error.
        
        Args:
            message: Description of the error.
            failed_requirements: List of requirement names that failed.
        """
        super().__init__(message)
        self.failed_requirements = failed_requirements or []


class PasswordService:
    """Service for secure password hashing and verification.
    
    Uses Argon2id algorithm, which is the recommended algorithm
    for password hashing per OWASP guidelines.
    
    Argon2 Parameters:
        - time_cost: Number of iterations (default: 3)
        - memory_cost: Memory usage in KiB (default: 65536 = 64MB)
        - parallelism: Number of parallel threads (default: 4)
        - hash_len: Length of the hash in bytes (default: 32)
        - salt_len: Length of the salt in bytes (default: 16)
    
    Example:
        >>> service = PasswordService()
        >>> hashed = service.hash("mypassword")
        >>> service.verify("mypassword", hashed)
        True
    """

    def __init__(
        self,
        time_cost: int = 3,
        memory_cost: int = 65536,
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 16,
    ) -> None:
        """Initialize password service with Argon2 parameters.
        
        Args:
            time_cost: Number of iterations.
            memory_cost: Memory usage in KiB.
            parallelism: Number of parallel threads.
            hash_len: Length of the hash in bytes.
            salt_len: Length of the salt in bytes.
        """
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )

    def hash(self, password: str) -> str:
        """Hash a password using Argon2id.
        
        Args:
            password: The plain text password.
            
        Returns:
            The hashed password string (includes algorithm params and salt).
            
        Example:
            >>> hashed = service.hash("mypassword")
            >>> hashed.startswith("$argon2id$")
            True
        """
        return self._hasher.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash.
        
        Args:
            password: The plain text password to verify.
            hashed: The hashed password to check against.
            
        Returns:
            True if the password matches, False otherwise.
            
        Example:
            >>> hashed = service.hash("mypassword")
            >>> service.verify("mypassword", hashed)
            True
            >>> service.verify("wrongpassword", hashed)
            False
        """
        try:
            self._hasher.verify(hashed, password)
            return True
        except (VerifyMismatchError, InvalidHashError):
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """Check if a hash needs to be rehashed.
        
        This is useful when Argon2 parameters have been updated.
        If True, you should verify the password and create a new hash.
        
        Args:
            hashed: The hashed password to check.
            
        Returns:
            True if the hash should be regenerated with current parameters.
            
        Example:
            >>> if service.needs_rehash(stored_hash):
            ...     if service.verify(password, stored_hash):
            ...         new_hash = service.hash(password)
            ...         # Store new_hash
        """
        return self._hasher.check_needs_rehash(hashed)


def check_password_strength(
    password: str,
    *,
    min_length: int = 8,
    require_uppercase: bool = False,
    require_lowercase: bool = False,
    require_digit: bool = False,
    require_special: bool = False,
    special_characters: str = "!@#$%^&*()_+-=[]{}|;':\",./<>?",
) -> bool:
    """Check if a password meets strength requirements.
    
    Args:
        password: The password to check.
        min_length: Minimum password length (default: 8).
        require_uppercase: Require at least one uppercase letter.
        require_lowercase: Require at least one lowercase letter.
        require_digit: Require at least one digit.
        require_special: Require at least one special character.
        special_characters: Set of allowed special characters.
        
    Returns:
        True if the password meets all requirements.
        
    Raises:
        PasswordStrengthError: If the password fails any requirement.
        
    Example:
        >>> check_password_strength("SecureP@ssw0rd!")
        True
        >>> check_password_strength("weak", min_length=8)
        Traceback (most recent call last):
            ...
        PasswordStrengthError: Password must be at least 8 characters long
    """
    errors: list[str] = []
    failed_requirements: list[str] = []

    # Check minimum length
    if len(password) < min_length:
        errors.append(
            f"Password must be at least {min_length} characters long"
        )
        failed_requirements.append("min_length")

    # Check uppercase requirement
    if require_uppercase and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
        failed_requirements.append("uppercase")

    # Check lowercase requirement
    if require_lowercase and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
        failed_requirements.append("lowercase")

    # Check digit requirement
    if require_digit and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")
        failed_requirements.append("digit")

    # Check special character requirement
    if require_special:
        escaped_chars = re.escape(special_characters)
        if not re.search(f"[{escaped_chars}]", password):
            errors.append("Password must contain at least one special character")
            failed_requirements.append("special")

    if errors:
        raise PasswordStrengthError(
            "; ".join(errors),
            failed_requirements=failed_requirements,
        )

    return True


__all__ = [
    "PasswordService",
    "PasswordStrengthError",
    "check_password_strength",
]
