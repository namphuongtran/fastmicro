"""
HTTP status code constants with helper methods.

This module provides a comprehensive enum of HTTP status codes with
utility methods for checking status categories and retrieving reason phrases.

Example:
    >>> from shared.constants import HTTPStatus
    >>> if HTTPStatus.is_success(response.status_code):
    ...     print("Request succeeded!")
    >>> print(HTTPStatus.get_reason_phrase(404))
    'Not Found'
"""

from __future__ import annotations

from enum import IntEnum

__all__ = ["HTTP_REASON_PHRASES", "HTTPStatus"]


# Module-level reason phrases mapping - kept outside enum for Python 3.14 compatibility
HTTP_REASON_PHRASES: dict[int, str] = {
    100: "Continue",
    101: "Switching Protocols",
    102: "Processing",
    103: "Early Hints",
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    207: "Multi-Status",
    208: "Already Reported",
    226: "IM Used",
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Payload Too Large",
    414: "URI Too Long",
    415: "Unsupported Media Type",
    416: "Range Not Satisfiable",
    417: "Expectation Failed",
    418: "I'm a Teapot",
    421: "Misdirected Request",
    422: "Unprocessable Entity",
    423: "Locked",
    424: "Failed Dependency",
    425: "Too Early",
    426: "Upgrade Required",
    428: "Precondition Required",
    429: "Too Many Requests",
    431: "Request Header Fields Too Large",
    451: "Unavailable For Legal Reasons",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported",
    506: "Variant Also Negotiates",
    507: "Insufficient Storage",
    508: "Loop Detected",
    510: "Not Extended",
    511: "Network Authentication Required",
}


class HTTPStatus(IntEnum):
    """
    HTTP status codes as defined in RFC 7231 and related specifications.

    Each status code includes its standard reason phrase and provides
    helper methods for category checking.

    Example:
        >>> HTTPStatus.OK
        <HTTPStatus.OK: 200>
        >>> HTTPStatus.OK.reason
        'OK'
        >>> HTTPStatus.is_success(200)
        True
    """

    # 1xx Informational
    CONTINUE = 100
    SWITCHING_PROTOCOLS = 101
    PROCESSING = 102
    EARLY_HINTS = 103

    # 2xx Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NON_AUTHORITATIVE_INFORMATION = 203
    NO_CONTENT = 204
    RESET_CONTENT = 205
    PARTIAL_CONTENT = 206
    MULTI_STATUS = 207
    ALREADY_REPORTED = 208
    IM_USED = 226

    # 3xx Redirection
    MULTIPLE_CHOICES = 300
    MOVED_PERMANENTLY = 301
    FOUND = 302
    SEE_OTHER = 303
    NOT_MODIFIED = 304
    USE_PROXY = 305
    TEMPORARY_REDIRECT = 307
    PERMANENT_REDIRECT = 308

    # 4xx Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    PAYMENT_REQUIRED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    PROXY_AUTHENTICATION_REQUIRED = 407
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    GONE = 410
    LENGTH_REQUIRED = 411
    PRECONDITION_FAILED = 412
    PAYLOAD_TOO_LARGE = 413
    URI_TOO_LONG = 414
    UNSUPPORTED_MEDIA_TYPE = 415
    RANGE_NOT_SATISFIABLE = 416
    EXPECTATION_FAILED = 417
    IM_A_TEAPOT = 418
    MISDIRECTED_REQUEST = 421
    UNPROCESSABLE_ENTITY = 422
    LOCKED = 423
    FAILED_DEPENDENCY = 424
    TOO_EARLY = 425
    UPGRADE_REQUIRED = 426
    PRECONDITION_REQUIRED = 428
    TOO_MANY_REQUESTS = 429
    REQUEST_HEADER_FIELDS_TOO_LARGE = 431
    UNAVAILABLE_FOR_LEGAL_REASONS = 451

    # 5xx Server Errors
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    HTTP_VERSION_NOT_SUPPORTED = 505
    VARIANT_ALSO_NEGOTIATES = 506
    INSUFFICIENT_STORAGE = 507
    LOOP_DETECTED = 508
    NOT_EXTENDED = 510
    NETWORK_AUTHENTICATION_REQUIRED = 511

    @property
    def reason(self) -> str:
        """
        Get the standard reason phrase for this status code.

        Returns:
            The HTTP reason phrase (e.g., "OK", "Not Found").
        """
        return HTTP_REASON_PHRASES.get(self.value, "Unknown")

    @classmethod
    def get_reason_phrase(cls, status_code: int) -> str:
        """
        Get the reason phrase for any status code.

        Args:
            status_code: The HTTP status code.

        Returns:
            The reason phrase, or "Unknown" if not recognized.

        Example:
            >>> HTTPStatus.get_reason_phrase(404)
            'Not Found'
        """
        return HTTP_REASON_PHRASES.get(status_code, "Unknown")

    @staticmethod
    def is_informational(status_code: int) -> bool:
        """
        Check if status code is informational (1xx).

        Args:
            status_code: The HTTP status code to check.

        Returns:
            True if the status code is 1xx.
        """
        return 100 <= status_code < 200

    @staticmethod
    def is_success(status_code: int) -> bool:
        """
        Check if status code indicates success (2xx).

        Args:
            status_code: The HTTP status code to check.

        Returns:
            True if the status code is 2xx.
        """
        return 200 <= status_code < 300

    @staticmethod
    def is_redirect(status_code: int) -> bool:
        """
        Check if status code indicates redirection (3xx).

        Args:
            status_code: The HTTP status code to check.

        Returns:
            True if the status code is 3xx.
        """
        return 300 <= status_code < 400

    @staticmethod
    def is_client_error(status_code: int) -> bool:
        """
        Check if status code indicates client error (4xx).

        Args:
            status_code: The HTTP status code to check.

        Returns:
            True if the status code is 4xx.
        """
        return 400 <= status_code < 500

    @staticmethod
    def is_server_error(status_code: int) -> bool:
        """
        Check if status code indicates server error (5xx).

        Args:
            status_code: The HTTP status code to check.

        Returns:
            True if the status code is 5xx.
        """
        return 500 <= status_code < 600

    @staticmethod
    def is_error(status_code: int) -> bool:
        """
        Check if status code indicates any error (4xx or 5xx).

        Args:
            status_code: The HTTP status code to check.

        Returns:
            True if the status code is 4xx or 5xx.
        """
        return status_code >= 400

    @classmethod
    def success_codes(cls) -> list[int]:
        """
        Get all success status codes (2xx).

        Returns:
            List of all 2xx status codes defined in this enum.
        """
        return [s.value for s in cls if 200 <= s.value < 300]

    @classmethod
    def client_error_codes(cls) -> list[int]:
        """
        Get all client error status codes (4xx).

        Returns:
            List of all 4xx status codes defined in this enum.
        """
        return [s.value for s in cls if 400 <= s.value < 500]

    @classmethod
    def server_error_codes(cls) -> list[int]:
        """
        Get all server error status codes (5xx).

        Returns:
            List of all 5xx status codes defined in this enum.
        """
        return [s.value for s in cls if 500 <= s.value < 600]
