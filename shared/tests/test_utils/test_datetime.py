"""Tests for shared.utils.datetime module.

This module tests datetime utilities including timezone handling,
ISO formatting, relative time calculations, and date arithmetic.
"""

from __future__ import annotations

import datetime
from datetime import timedelta, timezone
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    pass

# Import after the module is implemented
from shared.utils.datetime import (
    format_iso8601,
    format_relative_time,
    get_date_range,
    is_business_day,
    now_utc,
    parse_iso8601,
    start_of_day,
    end_of_day,
    utc_timestamp,
)


class TestNowUtc:
    """Tests for now_utc function."""

    def test_returns_datetime(self) -> None:
        """Should return a datetime object."""
        result = now_utc()
        assert isinstance(result, datetime.datetime)

    def test_has_utc_timezone(self) -> None:
        """Should return datetime with UTC timezone."""
        result = now_utc()
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_is_close_to_current_time(self) -> None:
        """Should return time close to current time."""
        before = datetime.datetime.now(tz=timezone.utc)
        result = now_utc()
        after = datetime.datetime.now(tz=timezone.utc)
        
        assert before <= result <= after


class TestUtcTimestamp:
    """Tests for utc_timestamp function."""

    def test_returns_float(self) -> None:
        """Should return a float timestamp."""
        result = utc_timestamp()
        assert isinstance(result, float)

    def test_is_positive(self) -> None:
        """Should return positive timestamp."""
        result = utc_timestamp()
        assert result > 0

    def test_is_close_to_current_time(self) -> None:
        """Should return timestamp close to current time."""
        before = datetime.datetime.now(tz=timezone.utc).timestamp()
        result = utc_timestamp()
        after = datetime.datetime.now(tz=timezone.utc).timestamp()
        
        assert before <= result <= after


class TestFormatIso8601:
    """Tests for format_iso8601 function."""

    def test_formats_datetime_with_timezone(self) -> None:
        """Should format datetime with timezone to ISO8601."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = format_iso8601(dt)
        assert result == "2024-01-15T10:30:45+00:00"

    def test_formats_datetime_without_timezone_as_utc(self) -> None:
        """Should treat naive datetime as UTC."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45)
        result = format_iso8601(dt)
        assert result == "2024-01-15T10:30:45+00:00"

    def test_formats_with_microseconds(self) -> None:
        """Should include microseconds when present."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45, 123456, tzinfo=timezone.utc)
        result = format_iso8601(dt, include_microseconds=True)
        assert ".123456" in result

    def test_excludes_microseconds_by_default(self) -> None:
        """Should exclude microseconds by default."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45, 123456, tzinfo=timezone.utc)
        result = format_iso8601(dt)
        assert "123456" not in result


class TestParseIso8601:
    """Tests for parse_iso8601 function."""

    def test_parses_iso8601_with_timezone(self) -> None:
        """Should parse ISO8601 string with timezone."""
        result = parse_iso8601("2024-01-15T10:30:45+00:00")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45
        assert result.tzinfo is not None

    def test_parses_iso8601_with_z_suffix(self) -> None:
        """Should parse ISO8601 string with Z suffix."""
        result = parse_iso8601("2024-01-15T10:30:45Z")
        assert result.tzinfo is not None
        assert result.utcoffset() == timedelta(0)

    def test_parses_with_microseconds(self) -> None:
        """Should parse string with microseconds."""
        result = parse_iso8601("2024-01-15T10:30:45.123456+00:00")
        assert result.microsecond == 123456

    def test_raises_on_invalid_format(self) -> None:
        """Should raise ValueError on invalid format."""
        with pytest.raises(ValueError, match="Invalid ISO 8601"):
            parse_iso8601("not-a-date")

    def test_handles_positive_offset(self) -> None:
        """Should handle positive timezone offset."""
        result = parse_iso8601("2024-01-15T10:30:45+05:30")
        offset = result.utcoffset()
        assert offset is not None
        assert offset.total_seconds() == 5.5 * 3600


class TestFormatRelativeTime:
    """Tests for format_relative_time function."""

    def test_just_now(self) -> None:
        """Should show 'just now' for recent times."""
        dt = now_utc() - timedelta(seconds=5)
        result = format_relative_time(dt)
        assert "just now" in result.lower()

    def test_seconds_ago(self) -> None:
        """Should show seconds ago."""
        dt = now_utc() - timedelta(seconds=30)
        result = format_relative_time(dt)
        assert "second" in result.lower()

    def test_minutes_ago(self) -> None:
        """Should show minutes ago."""
        dt = now_utc() - timedelta(minutes=5)
        result = format_relative_time(dt)
        assert "minute" in result.lower()

    def test_hours_ago(self) -> None:
        """Should show hours ago."""
        dt = now_utc() - timedelta(hours=3)
        result = format_relative_time(dt)
        assert "hour" in result.lower()

    def test_days_ago(self) -> None:
        """Should show days ago."""
        dt = now_utc() - timedelta(days=2)
        result = format_relative_time(dt)
        assert "day" in result.lower()

    def test_weeks_ago(self) -> None:
        """Should show weeks ago."""
        dt = now_utc() - timedelta(weeks=2)
        result = format_relative_time(dt)
        assert "week" in result.lower()

    def test_months_ago(self) -> None:
        """Should show months ago."""
        dt = now_utc() - timedelta(days=60)
        result = format_relative_time(dt)
        assert "month" in result.lower()

    def test_future_time(self) -> None:
        """Should handle future times."""
        dt = now_utc() + timedelta(hours=2)
        result = format_relative_time(dt)
        assert "from now" in result.lower() or "in " in result.lower()


class TestStartOfDay:
    """Tests for start_of_day function."""

    def test_returns_midnight(self) -> None:
        """Should return midnight of the given date."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = start_of_day(dt)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_preserves_date(self) -> None:
        """Should preserve the date."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = start_of_day(dt)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_preserves_timezone(self) -> None:
        """Should preserve the timezone."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = start_of_day(dt)
        assert result.tzinfo == timezone.utc


class TestEndOfDay:
    """Tests for end_of_day function."""

    def test_returns_end_of_day(self) -> None:
        """Should return 23:59:59.999999 of the given date."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = end_of_day(dt)
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        assert result.microsecond == 999999

    def test_preserves_date(self) -> None:
        """Should preserve the date."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = end_of_day(dt)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15


class TestIsBusinessDay:
    """Tests for is_business_day function."""

    def test_weekday_is_business_day(self) -> None:
        """Monday-Friday should be business days."""
        # Monday
        monday = datetime.date(2024, 1, 15)
        assert is_business_day(monday) is True
        
        # Friday
        friday = datetime.date(2024, 1, 19)
        assert is_business_day(friday) is True

    def test_weekend_is_not_business_day(self) -> None:
        """Saturday-Sunday should not be business days."""
        saturday = datetime.date(2024, 1, 20)
        sunday = datetime.date(2024, 1, 21)
        
        assert is_business_day(saturday) is False
        assert is_business_day(sunday) is False

    def test_accepts_datetime(self) -> None:
        """Should accept datetime objects."""
        monday_dt = datetime.datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        assert is_business_day(monday_dt) is True


class TestGetDateRange:
    """Tests for get_date_range function."""

    def test_returns_list_of_dates(self) -> None:
        """Should return list of dates."""
        start = datetime.date(2024, 1, 1)
        end = datetime.date(2024, 1, 5)
        
        result = get_date_range(start, end)
        
        assert len(result) == 5
        assert all(isinstance(d, datetime.date) for d in result)

    def test_includes_start_and_end(self) -> None:
        """Should include both start and end dates."""
        start = datetime.date(2024, 1, 1)
        end = datetime.date(2024, 1, 3)
        
        result = get_date_range(start, end)
        
        assert result[0] == start
        assert result[-1] == end

    def test_single_day_range(self) -> None:
        """Should handle single day range."""
        date = datetime.date(2024, 1, 15)
        result = get_date_range(date, date)
        
        assert len(result) == 1
        assert result[0] == date

    def test_reversed_dates_returns_empty(self) -> None:
        """Should return empty list when start > end."""
        start = datetime.date(2024, 1, 5)
        end = datetime.date(2024, 1, 1)
        
        result = get_date_range(start, end)
        
        assert result == []
