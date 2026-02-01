"""Tests for shared.utils.validation module.

This module tests input validation utilities including common validators,
data sanitization, and validation result handling.
"""

from __future__ import annotations

from shared.utils.validation import (
    ValidationResult,
    is_valid_email,
    is_valid_url,
    is_valid_uuid,
    sanitize_html,
    validate_length,
    validate_range,
    validate_required,
)


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_valid_result(self) -> None:
        """Should create valid result."""
        result = ValidationResult.valid()
        assert result.is_valid is True
        assert result.errors == []

    def test_invalid_result_with_single_error(self) -> None:
        """Should create invalid result with single error."""
        result = ValidationResult.invalid("Field is required")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "required" in result.errors[0].lower()

    def test_invalid_result_with_multiple_errors(self) -> None:
        """Should create invalid result with multiple errors."""
        result = ValidationResult.invalid_multiple(["Error 1", "Error 2"])
        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_combine_valid_results(self) -> None:
        """Should combine valid results."""
        r1 = ValidationResult.valid()
        r2 = ValidationResult.valid()
        combined = r1.combine(r2)
        assert combined.is_valid is True

    def test_combine_invalid_results(self) -> None:
        """Should combine invalid results."""
        r1 = ValidationResult.invalid("Error 1")
        r2 = ValidationResult.invalid("Error 2")
        combined = r1.combine(r2)
        assert combined.is_valid is False
        assert len(combined.errors) == 2

    def test_combine_mixed_results(self) -> None:
        """Should combine mixed results."""
        r1 = ValidationResult.valid()
        r2 = ValidationResult.invalid("Error")
        combined = r1.combine(r2)
        assert combined.is_valid is False

    def test_bool_conversion(self) -> None:
        """Should convert to bool based on validity."""
        assert bool(ValidationResult.valid()) is True
        assert bool(ValidationResult.invalid("Error")) is False


class TestIsValidEmail:
    """Tests for is_valid_email function."""

    def test_valid_email(self) -> None:
        """Should return True for valid email."""
        assert is_valid_email("user@example.com") is True

    def test_valid_email_with_plus(self) -> None:
        """Should accept email with plus sign."""
        assert is_valid_email("user+tag@example.com") is True

    def test_valid_email_with_subdomain(self) -> None:
        """Should accept email with subdomain."""
        assert is_valid_email("user@mail.example.com") is True

    def test_invalid_email_no_at(self) -> None:
        """Should return False for email without @."""
        assert is_valid_email("userexample.com") is False

    def test_invalid_email_no_domain(self) -> None:
        """Should return False for email without domain."""
        assert is_valid_email("user@") is False

    def test_invalid_email_no_tld(self) -> None:
        """Should return False for email without TLD."""
        assert is_valid_email("user@example") is False

    def test_empty_string(self) -> None:
        """Should return False for empty string."""
        assert is_valid_email("") is False

    def test_whitespace(self) -> None:
        """Should return False for whitespace."""
        assert is_valid_email("   ") is False


class TestIsValidUrl:
    """Tests for is_valid_url function."""

    def test_valid_http_url(self) -> None:
        """Should return True for valid HTTP URL."""
        assert is_valid_url("http://example.com") is True

    def test_valid_https_url(self) -> None:
        """Should return True for valid HTTPS URL."""
        assert is_valid_url("https://example.com") is True

    def test_valid_url_with_path(self) -> None:
        """Should accept URL with path."""
        assert is_valid_url("https://example.com/path/to/page") is True

    def test_valid_url_with_query(self) -> None:
        """Should accept URL with query parameters."""
        assert is_valid_url("https://example.com?query=value") is True

    def test_invalid_url_no_scheme(self) -> None:
        """Should return False for URL without scheme."""
        assert is_valid_url("example.com") is False

    def test_invalid_url_no_domain(self) -> None:
        """Should return False for URL without domain."""
        assert is_valid_url("http://") is False

    def test_empty_string(self) -> None:
        """Should return False for empty string."""
        assert is_valid_url("") is False


class TestIsValidUuid:
    """Tests for is_valid_uuid function."""

    def test_valid_uuid(self) -> None:
        """Should return True for valid UUID."""
        assert is_valid_uuid("12345678-1234-5678-1234-567812345678") is True

    def test_valid_uuid_uppercase(self) -> None:
        """Should accept uppercase UUID."""
        assert is_valid_uuid("12345678-1234-5678-1234-567812345678".upper()) is True

    def test_valid_uuid_without_dashes(self) -> None:
        """Should accept UUID without dashes."""
        assert is_valid_uuid("12345678123456781234567812345678") is True

    def test_invalid_uuid_wrong_length(self) -> None:
        """Should return False for wrong length."""
        assert is_valid_uuid("12345678-1234") is False

    def test_invalid_uuid_invalid_chars(self) -> None:
        """Should return False for invalid characters."""
        assert is_valid_uuid("ZZZZZZZZ-ZZZZ-ZZZZ-ZZZZ-ZZZZZZZZZZZZ") is False

    def test_empty_string(self) -> None:
        """Should return False for empty string."""
        assert is_valid_uuid("") is False


class TestValidateRequired:
    """Tests for validate_required function."""

    def test_non_empty_string(self) -> None:
        """Should return valid for non-empty string."""
        result = validate_required("value", "field_name")
        assert result.is_valid is True

    def test_empty_string(self) -> None:
        """Should return invalid for empty string."""
        result = validate_required("", "field_name")
        assert result.is_valid is False
        assert "field_name" in result.errors[0]

    def test_none_value(self) -> None:
        """Should return invalid for None."""
        result = validate_required(None, "field_name")
        assert result.is_valid is False

    def test_whitespace_only(self) -> None:
        """Should return invalid for whitespace only."""
        result = validate_required("   ", "field_name")
        assert result.is_valid is False

    def test_zero_is_valid(self) -> None:
        """Should accept zero as valid."""
        result = validate_required(0, "field_name")
        assert result.is_valid is True

    def test_false_is_valid(self) -> None:
        """Should accept False as valid."""
        result = validate_required(False, "field_name")
        assert result.is_valid is True


class TestValidateLength:
    """Tests for validate_length function."""

    def test_within_range(self) -> None:
        """Should return valid when within range."""
        result = validate_length("hello", "field", min_length=1, max_length=10)
        assert result.is_valid is True

    def test_too_short(self) -> None:
        """Should return invalid when too short."""
        result = validate_length("hi", "field", min_length=5)
        assert result.is_valid is False
        assert "at least" in result.errors[0].lower()

    def test_too_long(self) -> None:
        """Should return invalid when too long."""
        result = validate_length("hello world", "field", max_length=5)
        assert result.is_valid is False
        assert "at most" in result.errors[0].lower()

    def test_exact_min_length(self) -> None:
        """Should accept exact min length."""
        result = validate_length("hello", "field", min_length=5)
        assert result.is_valid is True

    def test_exact_max_length(self) -> None:
        """Should accept exact max length."""
        result = validate_length("hello", "field", max_length=5)
        assert result.is_valid is True


class TestValidateRange:
    """Tests for validate_range function."""

    def test_within_range(self) -> None:
        """Should return valid when within range."""
        result = validate_range(5, "field", min_value=1, max_value=10)
        assert result.is_valid is True

    def test_below_min(self) -> None:
        """Should return invalid when below min."""
        result = validate_range(0, "field", min_value=1)
        assert result.is_valid is False

    def test_above_max(self) -> None:
        """Should return invalid when above max."""
        result = validate_range(100, "field", max_value=10)
        assert result.is_valid is False

    def test_exact_min_value(self) -> None:
        """Should accept exact min value."""
        result = validate_range(1, "field", min_value=1)
        assert result.is_valid is True

    def test_exact_max_value(self) -> None:
        """Should accept exact max value."""
        result = validate_range(10, "field", max_value=10)
        assert result.is_valid is True

    def test_float_values(self) -> None:
        """Should work with float values."""
        result = validate_range(5.5, "field", min_value=1.0, max_value=10.0)
        assert result.is_valid is True


class TestSanitizeHtml:
    """Tests for sanitize_html function."""

    def test_removes_script_tags(self) -> None:
        """Should remove script tags."""
        result = sanitize_html("<script>alert('xss')</script>Hello")
        assert "<script>" not in result
        assert "alert" not in result
        assert "Hello" in result

    def test_removes_onclick_handlers(self) -> None:
        """Should remove onclick handlers."""
        result = sanitize_html("<div onclick='alert()'>Hello</div>")
        assert "onclick" not in result

    def test_removes_javascript_urls(self) -> None:
        """Should remove javascript: URLs."""
        result = sanitize_html("<a href='javascript:alert()'>Click</a>")
        assert "javascript:" not in result

    def test_preserves_safe_content(self) -> None:
        """Should preserve safe HTML content."""
        result = sanitize_html("<p>Hello <strong>World</strong></p>")
        assert "Hello" in result
        assert "World" in result

    def test_handles_plain_text(self) -> None:
        """Should handle plain text without HTML."""
        result = sanitize_html("Hello World")
        assert result == "Hello World"

    def test_empty_string(self) -> None:
        """Should handle empty string."""
        assert sanitize_html("") == ""
