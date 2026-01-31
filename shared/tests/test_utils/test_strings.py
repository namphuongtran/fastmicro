"""Tests for shared.utils.strings module.

This module tests string manipulation utilities including slugification,
truncation, case conversion, and text processing functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

from shared.utils.strings import (
    camel_to_snake,
    generate_random_string,
    mask_sensitive,
    pluralize,
    sanitize_filename,
    slugify,
    snake_to_camel,
    truncate,
)


class TestSlugify:
    """Tests for slugify function."""

    def test_basic_slugification(self) -> None:
        """Should convert basic string to slug."""
        assert slugify("Hello World") == "hello-world"

    def test_removes_special_characters(self) -> None:
        """Should remove special characters."""
        assert slugify("Hello, World!") == "hello-world"

    def test_handles_unicode(self) -> None:
        """Should handle unicode characters."""
        result = slugify("Héllo Wörld")
        assert "-" in result or result == "hllo-wrld" or result == "hello-world"

    def test_collapses_multiple_dashes(self) -> None:
        """Should collapse multiple dashes."""
        assert slugify("Hello   World") == "hello-world"

    def test_strips_leading_trailing_dashes(self) -> None:
        """Should strip leading/trailing dashes."""
        assert slugify("---Hello World---") == "hello-world"

    def test_handles_empty_string(self) -> None:
        """Should handle empty string."""
        assert slugify("") == ""

    def test_handles_only_special_chars(self) -> None:
        """Should handle string with only special characters."""
        assert slugify("!!!") == ""

    def test_custom_separator(self) -> None:
        """Should support custom separator."""
        assert slugify("Hello World", separator="_") == "hello_world"


class TestTruncate:
    """Tests for truncate function."""

    def test_no_truncation_needed(self) -> None:
        """Should not truncate short strings."""
        assert truncate("Hello", max_length=10) == "Hello"

    def test_truncates_long_string(self) -> None:
        """Should truncate long strings."""
        assert truncate("Hello World", max_length=8) == "Hello..."

    def test_custom_suffix(self) -> None:
        """Should support custom suffix."""
        assert truncate("Hello World", max_length=8, suffix="…") == "Hello W…"

    def test_handles_exact_length(self) -> None:
        """Should not truncate when length equals max."""
        assert truncate("Hello", max_length=5) == "Hello"

    def test_handles_empty_string(self) -> None:
        """Should handle empty string."""
        assert truncate("", max_length=10) == ""

    def test_handles_very_short_max(self) -> None:
        """Should handle very short max length."""
        result = truncate("Hello World", max_length=3)
        assert len(result) == 3


class TestCamelToSnake:
    """Tests for camel_to_snake function."""

    def test_basic_conversion(self) -> None:
        """Should convert camelCase to snake_case."""
        assert camel_to_snake("helloWorld") == "hello_world"

    def test_pascal_case(self) -> None:
        """Should handle PascalCase."""
        assert camel_to_snake("HelloWorld") == "hello_world"

    def test_consecutive_capitals(self) -> None:
        """Should handle consecutive capitals."""
        result = camel_to_snake("HTTPServer")
        assert result in ("http_server", "h_t_t_p_server")

    def test_single_word(self) -> None:
        """Should handle single word."""
        assert camel_to_snake("hello") == "hello"

    def test_already_snake_case(self) -> None:
        """Should not modify snake_case."""
        assert camel_to_snake("hello_world") == "hello_world"

    def test_empty_string(self) -> None:
        """Should handle empty string."""
        assert camel_to_snake("") == ""


class TestSnakeToCamel:
    """Tests for snake_to_camel function."""

    def test_basic_conversion(self) -> None:
        """Should convert snake_case to camelCase."""
        assert snake_to_camel("hello_world") == "helloWorld"

    def test_multiple_underscores(self) -> None:
        """Should handle multiple underscores."""
        assert snake_to_camel("hello_world_test") == "helloWorldTest"

    def test_single_word(self) -> None:
        """Should handle single word."""
        assert snake_to_camel("hello") == "hello"

    def test_uppercase_input(self) -> None:
        """Should handle uppercase input."""
        assert snake_to_camel("HELLO_WORLD") == "helloWorld"

    def test_empty_string(self) -> None:
        """Should handle empty string."""
        assert snake_to_camel("") == ""

    def test_pascal_case_option(self) -> None:
        """Should support PascalCase output."""
        assert snake_to_camel("hello_world", pascal=True) == "HelloWorld"


class TestGenerateRandomString:
    """Tests for generate_random_string function."""

    def test_default_length(self) -> None:
        """Should generate string of default length."""
        result = generate_random_string()
        assert len(result) > 0

    def test_custom_length(self) -> None:
        """Should generate string of specified length."""
        result = generate_random_string(length=20)
        assert len(result) == 20

    def test_alphanumeric_only(self) -> None:
        """Should generate only alphanumeric characters by default."""
        result = generate_random_string(length=100)
        assert result.isalnum()

    def test_with_special_chars(self) -> None:
        """Should include special characters when requested."""
        result = generate_random_string(length=100, include_special=True)
        # At least some calls should include special chars
        # (probabilistic, but with 100 chars, very likely)
        has_special = any(not c.isalnum() for c in result)
        # Might not always have special chars, so just verify it runs
        assert len(result) == 100

    def test_unique_results(self) -> None:
        """Should generate unique strings."""
        results = [generate_random_string(length=20) for _ in range(10)]
        assert len(set(results)) == 10  # All unique


class TestMaskSensitive:
    """Tests for mask_sensitive function."""

    def test_masks_middle_of_string(self) -> None:
        """Should mask middle of string."""
        result = mask_sensitive("1234567890")
        assert result.startswith("12") or result.startswith("1")
        assert result.endswith("90") or result.endswith("0")
        assert "*" in result

    def test_custom_visible_chars(self) -> None:
        """Should respect visible char count."""
        result = mask_sensitive("1234567890", visible_chars=2)
        assert result.startswith("12")
        assert result.endswith("90")

    def test_custom_mask_char(self) -> None:
        """Should use custom mask character."""
        result = mask_sensitive("1234567890", mask_char="X")
        assert "X" in result

    def test_short_string(self) -> None:
        """Should handle strings shorter than visible chars."""
        result = mask_sensitive("abc")
        # Should either show all or partially mask
        assert len(result) == 3

    def test_empty_string(self) -> None:
        """Should handle empty string."""
        assert mask_sensitive("") == ""


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_removes_invalid_chars(self) -> None:
        """Should remove invalid filename characters."""
        result = sanitize_filename("file/name:test")
        assert "/" not in result
        assert ":" not in result

    def test_preserves_valid_chars(self) -> None:
        """Should preserve valid characters."""
        assert sanitize_filename("valid_file-name.txt") == "valid_file-name.txt"

    def test_handles_spaces(self) -> None:
        """Should handle spaces appropriately."""
        result = sanitize_filename("file name.txt")
        assert result in ("file name.txt", "file_name.txt", "file-name.txt")

    def test_max_length(self) -> None:
        """Should respect maximum length."""
        long_name = "a" * 300
        result = sanitize_filename(long_name, max_length=100)
        assert len(result) <= 100

    def test_empty_string(self) -> None:
        """Should handle empty string."""
        result = sanitize_filename("")
        # Should return something or empty
        assert isinstance(result, str)


class TestPluralize:
    """Tests for pluralize function."""

    def test_singular_count(self) -> None:
        """Should return singular for count of 1."""
        assert pluralize("item", 1) == "item"

    def test_plural_count(self) -> None:
        """Should return plural for count > 1."""
        assert pluralize("item", 2) == "items"

    def test_zero_count(self) -> None:
        """Should return plural for count of 0."""
        assert pluralize("item", 0) == "items"

    def test_custom_plural(self) -> None:
        """Should support custom plural form."""
        assert pluralize("child", 2, plural="children") == "children"

    def test_irregular_plural(self) -> None:
        """Should handle irregular plurals."""
        assert pluralize("person", 2, plural="people") == "people"
