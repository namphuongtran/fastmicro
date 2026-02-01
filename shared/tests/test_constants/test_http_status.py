"""
Unit tests for HTTP status code constants.

Tests cover:
- Status code values and categories
- Helper methods for checking status types
- Reason phrases
"""

from __future__ import annotations

from shared.constants.http_status import HTTPStatus


class TestHTTPStatusValues:
    """Tests for HTTP status code values."""

    # 2xx Success
    def test_ok(self) -> None:
        assert HTTPStatus.OK == 200

    def test_created(self) -> None:
        assert HTTPStatus.CREATED == 201

    def test_accepted(self) -> None:
        assert HTTPStatus.ACCEPTED == 202

    def test_no_content(self) -> None:
        assert HTTPStatus.NO_CONTENT == 204

    # 3xx Redirection
    def test_moved_permanently(self) -> None:
        assert HTTPStatus.MOVED_PERMANENTLY == 301

    def test_found(self) -> None:
        assert HTTPStatus.FOUND == 302

    def test_not_modified(self) -> None:
        assert HTTPStatus.NOT_MODIFIED == 304

    def test_temporary_redirect(self) -> None:
        assert HTTPStatus.TEMPORARY_REDIRECT == 307

    def test_permanent_redirect(self) -> None:
        assert HTTPStatus.PERMANENT_REDIRECT == 308

    # 4xx Client Errors
    def test_bad_request(self) -> None:
        assert HTTPStatus.BAD_REQUEST == 400

    def test_unauthorized(self) -> None:
        assert HTTPStatus.UNAUTHORIZED == 401

    def test_forbidden(self) -> None:
        assert HTTPStatus.FORBIDDEN == 403

    def test_not_found(self) -> None:
        assert HTTPStatus.NOT_FOUND == 404

    def test_method_not_allowed(self) -> None:
        assert HTTPStatus.METHOD_NOT_ALLOWED == 405

    def test_conflict(self) -> None:
        assert HTTPStatus.CONFLICT == 409

    def test_unprocessable_entity(self) -> None:
        assert HTTPStatus.UNPROCESSABLE_ENTITY == 422

    def test_too_many_requests(self) -> None:
        assert HTTPStatus.TOO_MANY_REQUESTS == 429

    # 5xx Server Errors
    def test_internal_server_error(self) -> None:
        assert HTTPStatus.INTERNAL_SERVER_ERROR == 500

    def test_bad_gateway(self) -> None:
        assert HTTPStatus.BAD_GATEWAY == 502

    def test_service_unavailable(self) -> None:
        assert HTTPStatus.SERVICE_UNAVAILABLE == 503

    def test_gateway_timeout(self) -> None:
        assert HTTPStatus.GATEWAY_TIMEOUT == 504


class TestHTTPStatusCategoryChecks:
    """Tests for status category helper methods."""

    def test_is_informational(self) -> None:
        """1xx status codes are informational."""
        assert HTTPStatus.is_informational(100)
        assert HTTPStatus.is_informational(101)
        assert not HTTPStatus.is_informational(200)
        assert not HTTPStatus.is_informational(400)

    def test_is_success(self) -> None:
        """2xx status codes indicate success."""
        assert HTTPStatus.is_success(200)
        assert HTTPStatus.is_success(201)
        assert HTTPStatus.is_success(204)
        assert not HTTPStatus.is_success(300)
        assert not HTTPStatus.is_success(400)

    def test_is_redirect(self) -> None:
        """3xx status codes indicate redirection."""
        assert HTTPStatus.is_redirect(301)
        assert HTTPStatus.is_redirect(302)
        assert HTTPStatus.is_redirect(307)
        assert not HTTPStatus.is_redirect(200)
        assert not HTTPStatus.is_redirect(400)

    def test_is_client_error(self) -> None:
        """4xx status codes indicate client errors."""
        assert HTTPStatus.is_client_error(400)
        assert HTTPStatus.is_client_error(404)
        assert HTTPStatus.is_client_error(422)
        assert not HTTPStatus.is_client_error(200)
        assert not HTTPStatus.is_client_error(500)

    def test_is_server_error(self) -> None:
        """5xx status codes indicate server errors."""
        assert HTTPStatus.is_server_error(500)
        assert HTTPStatus.is_server_error(502)
        assert HTTPStatus.is_server_error(503)
        assert not HTTPStatus.is_server_error(200)
        assert not HTTPStatus.is_server_error(400)

    def test_is_error(self) -> None:
        """4xx and 5xx are errors."""
        assert HTTPStatus.is_error(400)
        assert HTTPStatus.is_error(500)
        assert not HTTPStatus.is_error(200)
        assert not HTTPStatus.is_error(301)


class TestHTTPStatusReasonPhrases:
    """Tests for reason phrase retrieval."""

    def test_get_reason_phrase(self) -> None:
        """get_reason_phrase returns standard HTTP reason."""
        assert HTTPStatus.get_reason_phrase(200) == "OK"
        assert HTTPStatus.get_reason_phrase(201) == "Created"
        assert HTTPStatus.get_reason_phrase(400) == "Bad Request"
        assert HTTPStatus.get_reason_phrase(404) == "Not Found"
        assert HTTPStatus.get_reason_phrase(500) == "Internal Server Error"

    def test_get_reason_phrase_unknown_code(self) -> None:
        """get_reason_phrase returns 'Unknown' for unrecognized codes."""
        assert HTTPStatus.get_reason_phrase(999) == "Unknown"

    def test_reason_property(self) -> None:
        """HTTPStatus enum members have reason property."""
        assert HTTPStatus.OK.reason == "OK"
        assert HTTPStatus.NOT_FOUND.reason == "Not Found"
        assert HTTPStatus.INTERNAL_SERVER_ERROR.reason == "Internal Server Error"


class TestHTTPStatusAllCodes:
    """Tests for listing all codes."""

    def test_all_2xx_codes(self) -> None:
        """Get all success status codes."""
        codes = HTTPStatus.success_codes()
        assert 200 in codes
        assert 201 in codes
        assert 204 in codes
        assert all(200 <= c < 300 for c in codes)

    def test_all_4xx_codes(self) -> None:
        """Get all client error status codes."""
        codes = HTTPStatus.client_error_codes()
        assert 400 in codes
        assert 404 in codes
        assert 422 in codes
        assert all(400 <= c < 500 for c in codes)

    def test_all_5xx_codes(self) -> None:
        """Get all server error status codes."""
        codes = HTTPStatus.server_error_codes()
        assert 500 in codes
        assert 502 in codes
        assert 503 in codes
        assert all(500 <= c < 600 for c in codes)
