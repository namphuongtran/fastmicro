"""Consent domain entity - re-exported from shared library.

Canonical definitions live in ``shared.identity.entities.consent``.
"""

from shared.identity.entities.consent import (  # noqa: F401
    Consent,
    ConsentScope,
    Session,
)

__all__ = [
    "Consent",
    "ConsentScope",
    "Session",
]
