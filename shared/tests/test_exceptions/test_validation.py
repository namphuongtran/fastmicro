"""
Unit tests for validation exceptions.

Tests cover:
- Single field validation errors
- Multiple field errors
- Pydantic-compatible error format
- FieldError model
- Integration with HTTP 422 response
"""

from __future__ import annotations

from typing import Any

import pytest

from shared.exceptions.http import UnprocessableEntityException
from shared.exceptions.validation import (
    FieldError,
    ValidationException,
)


class TestFieldError:
    """Tests for FieldError model."""

    def test_creation_with_required_fields(self) -> None:
        """FieldError can be created with minimum required fields."""
        error = FieldError(
            loc=("body", "email"),
            msg="Invalid email format",
            type="value_error.email",
        )

        assert error.loc == ("body", "email")
        assert error.msg == "Invalid email format"
        assert error.type == "value_error.email"
        assert error.ctx is None

    def test_creation_with_context(self) -> None:
        """FieldError can include additional context."""
        error = FieldError(
            loc=("body", "age"),
            msg="Value must be greater than 0",
            type="value_error.number.not_gt",
            ctx={"limit_value": 0},
        )

        assert error.ctx == {"limit_value": 0}

    def test_to_dict_format(self) -> None:
        """FieldError.to_dict() matches Pydantic error format."""
        error = FieldError(
            loc=("body", "username"),
            msg="String too short",
            type="value_error.any_str.min_length",
            ctx={"limit_value": 3},
        )

        result = error.to_dict()

        assert result["loc"] == ["body", "username"]  # tuple -> list for JSON
        assert result["msg"] == "String too short"
        assert result["type"] == "value_error.any_str.min_length"
        assert result["ctx"] == {"limit_value": 3}

    def test_to_dict_excludes_none_ctx(self) -> None:
        """FieldError.to_dict() excludes ctx when None."""
        error = FieldError(
            loc=("body", "name"),
            msg="Required field",
            type="value_error.missing",
        )

        result = error.to_dict()

        assert "ctx" not in result

    def test_loc_as_string(self) -> None:
        """FieldError accepts single string location."""
        error = FieldError(
            loc=("email",),
            msg="Invalid",
            type="value_error",
        )

        assert error.loc == ("email",)

    def test_nested_location(self) -> None:
        """FieldError handles deeply nested locations."""
        error = FieldError(
            loc=("body", "user", "address", "zip_code"),
            msg="Invalid zip code format",
            type="value_error.str.regex",
        )

        assert len(error.loc) == 4
        result = error.to_dict()
        assert result["loc"] == ["body", "user", "address", "zip_code"]


class TestValidationException:
    """Tests for ValidationException class."""

    def test_inherits_from_unprocessable_entity(self) -> None:
        """ValidationException inherits from UnprocessableEntityException."""
        exc = ValidationException(errors=[])
        assert isinstance(exc, UnprocessableEntityException)
        assert exc.status_code == 422

    def test_single_error(self) -> None:
        """ValidationException can hold a single error."""
        error = FieldError(
            loc=("body", "email"),
            msg="Invalid email",
            type="value_error.email",
        )
        exc = ValidationException(errors=[error])

        assert len(exc.errors) == 1
        assert exc.errors[0].msg == "Invalid email"

    def test_multiple_errors(self) -> None:
        """ValidationException can hold multiple errors."""
        errors = [
            FieldError(loc=("body", "email"), msg="Invalid email", type="value_error.email"),
            FieldError(loc=("body", "age"), msg="Must be positive", type="value_error.number"),
            FieldError(loc=("body", "name"), msg="Required", type="value_error.missing"),
        ]
        exc = ValidationException(errors=errors)

        assert len(exc.errors) == 3

    def test_default_message(self) -> None:
        """ValidationException has descriptive default message."""
        errors = [
            FieldError(loc=("body", "email"), msg="Invalid", type="value_error"),
        ]
        exc = ValidationException(errors=errors)

        assert "validation" in exc.message.lower()

    def test_custom_message(self) -> None:
        """ValidationException accepts custom message."""
        exc = ValidationException(
            errors=[],
            message="Form validation failed",
        )

        assert exc.message == "Form validation failed"

    def test_error_code(self) -> None:
        """ValidationException has correct error code."""
        exc = ValidationException(errors=[])

        assert exc.error_code == "VALIDATION_ERROR"

    def test_to_response_includes_errors(self) -> None:
        """to_response() includes field errors in Pydantic format."""
        errors = [
            FieldError(loc=("body", "email"), msg="Invalid email", type="value_error.email"),
            FieldError(loc=("body", "age"), msg="Must be >= 0", type="value_error", ctx={"ge": 0}),
        ]
        exc = ValidationException(errors=errors)

        response = exc.to_response()

        body_errors = response["body"]["error"]["details"]["errors"]
        assert len(body_errors) == 2
        assert body_errors[0]["loc"] == ["body", "email"]
        assert body_errors[1]["ctx"] == {"ge": 0}

    def test_to_dict_includes_errors(self) -> None:
        """to_dict() includes field errors."""
        errors = [
            FieldError(loc=("name",), msg="Required", type="value_error.missing"),
        ]
        exc = ValidationException(errors=errors)

        result = exc.to_dict()

        assert "errors" in result["details"]
        assert len(result["details"]["errors"]) == 1


class TestValidationExceptionFactoryMethods:
    """Tests for ValidationException factory methods."""

    def test_from_field_errors_list(self) -> None:
        """from_errors() creates exception from list of dicts."""
        error_dicts = [
            {"loc": ("body", "email"), "msg": "Invalid", "type": "value_error"},
            {"loc": ("body", "name"), "msg": "Required", "type": "value_error.missing"},
        ]

        exc = ValidationException.from_errors(error_dicts)

        assert len(exc.errors) == 2
        assert exc.errors[0].loc == ("body", "email")

    def test_for_field_creates_single_error(self) -> None:
        """for_field() creates exception for single field."""
        exc = ValidationException.for_field(
            field="email",
            message="Invalid email format",
            error_type="value_error.email",
        )

        assert len(exc.errors) == 1
        assert exc.errors[0].loc == ("body", "email")
        assert exc.errors[0].msg == "Invalid email format"

    def test_for_field_with_location_prefix(self) -> None:
        """for_field() can specify location prefix."""
        exc = ValidationException.for_field(
            field="api_key",
            message="Invalid API key",
            error_type="value_error",
            location="header",
        )

        assert exc.errors[0].loc == ("header", "api_key")

    def test_for_missing_field(self) -> None:
        """for_missing_field() creates missing field error."""
        exc = ValidationException.for_missing_field("username")

        assert len(exc.errors) == 1
        assert exc.errors[0].type == "value_error.missing"
        assert "username" in exc.errors[0].msg.lower() or exc.errors[0].loc[-1] == "username"

    def test_for_invalid_type(self) -> None:
        """for_invalid_type() creates type error."""
        exc = ValidationException.for_invalid_type(
            field="age",
            expected_type="integer",
            actual_value="not_a_number",
        )

        assert len(exc.errors) == 1
        assert "type" in exc.errors[0].type.lower()


class TestValidationExceptionPydanticCompatibility:
    """Tests ensuring compatibility with Pydantic validation errors."""

    def test_from_pydantic_validation_error_format(
        self, sample_validation_errors: list[dict[str, Any]]
    ) -> None:
        """ValidationException can be created from Pydantic error format."""
        exc = ValidationException.from_errors(sample_validation_errors)

        assert len(exc.errors) == 2
        assert exc.errors[0].loc == ("body", "email")
        assert exc.errors[1].ctx == {"limit_value": 0}

    def test_error_format_matches_pydantic(self) -> None:
        """Error output format matches Pydantic's RequestValidationError."""
        errors = [
            FieldError(
                loc=("body", "items", 0, "price"),
                msg="ensure this value is greater than 0",
                type="value_error.number.not_gt",
                ctx={"limit_value": 0},
            ),
        ]
        exc = ValidationException(errors=errors)

        response = exc.to_response()
        error_detail = response["body"]["error"]["details"]["errors"][0]

        # Should match FastAPI/Pydantic format
        assert error_detail["loc"] == ["body", "items", 0, "price"]
        assert "msg" in error_detail
        assert "type" in error_detail


class TestValidationExceptionWithCorrelationId:
    """Tests for correlation ID support in validation exceptions."""

    def test_correlation_id_propagation(self) -> None:
        """ValidationException propagates correlation ID."""
        exc = ValidationException(
            errors=[],
            correlation_id="req-abc-123",
        )

        assert exc.correlation_id == "req-abc-123"

    def test_correlation_id_in_response(self) -> None:
        """Correlation ID appears in response."""
        exc = ValidationException(
            errors=[
                FieldError(loc=("body", "x"), msg="Invalid", type="error"),
            ],
            correlation_id="trace-xyz",
        )

        response = exc.to_response()

        assert response["body"]["error"]["correlation_id"] == "trace-xyz"
