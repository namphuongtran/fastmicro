"""Identity Admin Service.

Internal administration service for Identity Provider management.
This service handles OAuth2 client management, user administration,
and system configuration.

Security Notice:
    This service MUST be deployed on internal networks only.
    It should NOT be exposed to the public internet.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
