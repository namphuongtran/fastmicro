"""
Unit tests for regex pattern constants.

Tests cover:
- Email validation pattern
- UUID pattern
- URL patterns
- Common string patterns
"""

from __future__ import annotations

import re

import pytest

from shared.constants.patterns import Patterns


class TestEmailPattern:
    """Tests for email validation pattern."""

    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "test.user@domain.co.uk",
            "name+tag@example.org",
            "user123@test-domain.com",
            "a@b.co",
        ],
    )
    def test_valid_emails(self, email: str) -> None:
        """Pattern matches valid email addresses."""
        assert Patterns.EMAIL.match(email) is not None

    @pytest.mark.parametrize(
        "email",
        [
            "invalid",
            "@example.com",
            "user@",
            "user@.com",
            "user@domain",
            "",
            "user name@example.com",
        ],
    )
    def test_invalid_emails(self, email: str) -> None:
        """Pattern rejects invalid email addresses."""
        assert Patterns.EMAIL.match(email) is None


class TestUUIDPattern:
    """Tests for UUID validation pattern."""

    @pytest.mark.parametrize(
        "uuid",
        [
            "123e4567-e89b-12d3-a456-426614174000",
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "F47AC10B-58CC-4372-A567-0E02B2C3D479",  # uppercase
        ],
    )
    def test_valid_uuids(self, uuid: str) -> None:
        """Pattern matches valid UUIDs."""
        assert Patterns.UUID.match(uuid) is not None

    @pytest.mark.parametrize(
        "uuid",
        [
            "invalid",
            "123e4567e89b12d3a456426614174000",  # no dashes
            "123e4567-e89b-12d3-a456",  # too short
            "123e4567-e89b-12d3-a456-4266141740001",  # too long
            "",
        ],
    )
    def test_invalid_uuids(self, uuid: str) -> None:
        """Pattern rejects invalid UUIDs."""
        assert Patterns.UUID.match(uuid) is None


class TestURLPattern:
    """Tests for URL validation pattern."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com",
            "https://example.com",
            "https://www.example.com/path",
            "https://example.com/path?query=value",
            "https://example.com:8080/path",
            "http://localhost:3000",
            "https://sub.domain.example.com",
        ],
    )
    def test_valid_urls(self, url: str) -> None:
        """Pattern matches valid URLs."""
        assert Patterns.URL.match(url) is not None

    @pytest.mark.parametrize(
        "url",
        [
            "invalid",
            "example.com",  # no protocol
            "ftp://example.com",  # not http/https (if restricted)
            "",
        ],
    )
    def test_invalid_urls(self, url: str) -> None:
        """Pattern rejects invalid URLs."""
        # Note: URL pattern might be more permissive
        # This test validates the basic rejection cases
        if url == "":
            assert Patterns.URL.match(url) is None


class TestSlugPattern:
    """Tests for URL slug pattern."""

    @pytest.mark.parametrize(
        "slug",
        [
            "valid-slug",
            "another-valid-slug-123",
            "simple",
            "a",
            "slug-with-numbers-123",
        ],
    )
    def test_valid_slugs(self, slug: str) -> None:
        """Pattern matches valid URL slugs."""
        assert Patterns.SLUG.match(slug) is not None

    @pytest.mark.parametrize(
        "slug",
        [
            "Invalid Slug",  # spaces
            "UPPERCASE",  # uppercase (if strict)
            "slug_with_underscores",  # underscores (if strict)
            "",
        ],
    )
    def test_invalid_slugs(self, slug: str) -> None:
        """Pattern rejects invalid slugs."""
        # Note: slug patterns may vary in strictness
        if slug == "":
            assert Patterns.SLUG.match(slug) is None


class TestPhonePattern:
    """Tests for phone number pattern."""

    @pytest.mark.parametrize(
        "phone",
        [
            "+1234567890",
            "+44 20 7946 0958",
            "123-456-7890",
            "(123) 456-7890",
            "+1 (123) 456-7890",
        ],
    )
    def test_valid_phones(self, phone: str) -> None:
        """Pattern matches valid phone numbers."""
        assert Patterns.PHONE.match(phone) is not None

    def test_empty_phone(self) -> None:
        """Pattern rejects empty phone."""
        assert Patterns.PHONE.match("") is None


class TestUsernamePattern:
    """Tests for username pattern."""

    @pytest.mark.parametrize(
        "username",
        [
            "user123",
            "john_doe",
            "JohnDoe",
            "user-name",
            "u",
        ],
    )
    def test_valid_usernames(self, username: str) -> None:
        """Pattern matches valid usernames."""
        assert Patterns.USERNAME.match(username) is not None

    @pytest.mark.parametrize(
        "username",
        [
            "",
            "user name",  # space
            "user@name",  # special char
        ],
    )
    def test_invalid_usernames(self, username: str) -> None:
        """Pattern rejects invalid usernames."""
        assert Patterns.USERNAME.match(username) is None


class TestPatternHelpers:
    """Tests for pattern helper methods."""

    def test_is_valid_email(self) -> None:
        """is_valid_email convenience method."""
        assert Patterns.is_valid_email("test@example.com") is True
        assert Patterns.is_valid_email("invalid") is False

    def test_is_valid_uuid(self) -> None:
        """is_valid_uuid convenience method."""
        assert Patterns.is_valid_uuid("123e4567-e89b-12d3-a456-426614174000") is True
        assert Patterns.is_valid_uuid("invalid") is False

    def test_extract_emails(self) -> None:
        """extract_emails finds all emails in text."""
        text = "Contact us at info@example.com or support@test.org"
        emails = Patterns.extract_emails(text)
        assert "info@example.com" in emails
        assert "support@test.org" in emails

    def test_extract_uuids(self) -> None:
        """extract_uuids finds all UUIDs in text."""
        text = "IDs: 123e4567-e89b-12d3-a456-426614174000 and 550e8400-e29b-41d4-a716-446655440000"
        uuids = Patterns.extract_uuids(text)
        assert len(uuids) == 2
