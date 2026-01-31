"""
Datetime utilities for consistent timezone handling and formatting.

This module provides utilities for working with datetime objects including
timezone-aware operations, ISO 8601 formatting/parsing, relative time
calculations, and date arithmetic.

Example:
    >>> from shared.utils.datetime import now_utc, format_iso8601
    >>> dt = now_utc()
    >>> print(format_iso8601(dt))
    '2024-01-15T10:30:45+00:00'
"""

from __future__ import annotations

import datetime
from datetime import date, timedelta, timezone
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    pass

__all__ = [
    "now_utc",
    "utc_timestamp",
    "format_iso8601",
    "parse_iso8601",
    "format_relative_time",
    "start_of_day",
    "end_of_day",
    "is_business_day",
    "get_date_range",
]


def now_utc() -> datetime.datetime:
    """
    Get the current datetime in UTC timezone.

    Always returns a timezone-aware datetime object set to UTC.
    This ensures consistency across distributed systems.

    Returns:
        Current datetime in UTC.

    Example:
        >>> dt = now_utc()
        >>> dt.tzinfo
        datetime.timezone.utc
    """
    return datetime.datetime.now(tz=timezone.utc)


def utc_timestamp() -> float:
    """
    Get the current UTC timestamp as a float.

    Returns the number of seconds since the Unix epoch (1970-01-01 00:00:00 UTC).

    Returns:
        Current UTC timestamp as float.

    Example:
        >>> ts = utc_timestamp()
        >>> ts > 0
        True
    """
    return datetime.datetime.now(tz=timezone.utc).timestamp()


def format_iso8601(
    dt: datetime.datetime,
    *,
    include_microseconds: bool = False,
) -> str:
    """
    Format a datetime object as an ISO 8601 string.

    Handles timezone conversion and optional microseconds.
    Naive datetimes are assumed to be UTC.

    Args:
        dt: The datetime to format.
        include_microseconds: Whether to include microseconds in output.

    Returns:
        ISO 8601 formatted string.

    Example:
        >>> dt = datetime.datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        >>> format_iso8601(dt)
        '2024-01-15T10:30:00+00:00'
    """
    # Ensure timezone awareness
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if not include_microseconds:
        dt = dt.replace(microsecond=0)

    return dt.isoformat()


def parse_iso8601(value: str) -> datetime.datetime:
    """
    Parse an ISO 8601 formatted datetime string.

    Supports various ISO 8601 formats including:
    - Full datetime with timezone: 2024-01-15T10:30:45+00:00
    - UTC with Z suffix: 2024-01-15T10:30:45Z
    - With microseconds: 2024-01-15T10:30:45.123456+00:00

    Args:
        value: ISO 8601 formatted string.

    Returns:
        Parsed datetime object (always timezone-aware).

    Raises:
        ValueError: If the string cannot be parsed.

    Example:
        >>> parse_iso8601("2024-01-15T10:30:45Z")
        datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=datetime.timezone.utc)
    """
    # Handle Z suffix (Zulu time / UTC)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError as e:
        raise ValueError(f"Invalid ISO 8601 format: {value}") from e


def format_relative_time(dt: datetime.datetime) -> str:
    """
    Format a datetime as a human-readable relative time string.

    Examples: "just now", "5 minutes ago", "2 hours ago", "3 days ago"

    Args:
        dt: The datetime to format.

    Returns:
        Human-readable relative time string.

    Example:
        >>> from datetime import timedelta
        >>> dt = now_utc() - timedelta(minutes=5)
        >>> format_relative_time(dt)
        '5 minutes ago'
    """
    now = now_utc()
    
    # Ensure both have timezone info
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    diff = now - dt
    seconds = diff.total_seconds()
    
    # Handle future times
    if seconds < 0:
        return _format_future_time(abs(seconds))
    
    # Past times
    if seconds < 10:
        return "just now"
    elif seconds < 60:
        count = int(seconds)
        return f"{count} second{'s' if count != 1 else ''} ago"
    elif seconds < 3600:
        count = int(seconds // 60)
        return f"{count} minute{'s' if count != 1 else ''} ago"
    elif seconds < 86400:
        count = int(seconds // 3600)
        return f"{count} hour{'s' if count != 1 else ''} ago"
    elif seconds < 604800:  # 7 days
        count = int(seconds // 86400)
        return f"{count} day{'s' if count != 1 else ''} ago"
    elif seconds < 2592000:  # 30 days
        count = int(seconds // 604800)
        return f"{count} week{'s' if count != 1 else ''} ago"
    else:
        count = int(seconds // 2592000)
        return f"{count} month{'s' if count != 1 else ''} ago"


def _format_future_time(seconds: float) -> str:
    """Format future time (helper for format_relative_time)."""
    if seconds < 60:
        count = int(seconds)
        return f"in {count} second{'s' if count != 1 else ''}" if count > 10 else "just now"
    elif seconds < 3600:
        count = int(seconds // 60)
        return f"in {count} minute{'s' if count != 1 else ''}"
    elif seconds < 86400:
        count = int(seconds // 3600)
        return f"in {count} hour{'s' if count != 1 else ''}"
    elif seconds < 604800:
        count = int(seconds // 86400)
        return f"in {count} day{'s' if count != 1 else ''}"
    else:
        count = int(seconds // 604800)
        return f"in {count} week{'s' if count != 1 else ''}"


def start_of_day(dt: datetime.datetime) -> datetime.datetime:
    """
    Get the start of the day (midnight) for a given datetime.

    Args:
        dt: The datetime to get start of day for.

    Returns:
        Datetime at midnight (00:00:00.000000) on the same date.

    Example:
        >>> dt = datetime.datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        >>> start_of_day(dt).hour
        0
    """
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime.datetime) -> datetime.datetime:
    """
    Get the end of the day for a given datetime.

    Args:
        dt: The datetime to get end of day for.

    Returns:
        Datetime at 23:59:59.999999 on the same date.

    Example:
        >>> dt = datetime.datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        >>> end_of_day(dt).hour
        23
    """
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def is_business_day(d: Union[date, datetime.datetime]) -> bool:
    """
    Check if a date is a business day (Monday-Friday).

    Note: This does not account for holidays.

    Args:
        d: The date or datetime to check.

    Returns:
        True if the date is a weekday (Monday-Friday).

    Example:
        >>> is_business_day(date(2024, 1, 15))  # Monday
        True
        >>> is_business_day(date(2024, 1, 20))  # Saturday
        False
    """
    if isinstance(d, datetime.datetime):
        d = d.date()
    
    # weekday(): Monday = 0, Sunday = 6
    return d.weekday() < 5


def get_date_range(
    start: date,
    end: date,
) -> list[date]:
    """
    Get a list of dates between start and end (inclusive).

    Args:
        start: The start date.
        end: The end date.

    Returns:
        List of dates from start to end (inclusive).
        Empty list if start > end.

    Example:
        >>> get_date_range(date(2024, 1, 1), date(2024, 1, 3))
        [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    """
    if start > end:
        return []
    
    result = []
    current = start
    while current <= end:
        result.append(current)
        current += timedelta(days=1)
    
    return result
