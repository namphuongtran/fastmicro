"""Unit tests for domain value objects."""

import pytest

from identity_service.domain.value_objects import (
    CodeChallenge,
    Email,
    GrantType,
    Password,
    RedirectUri,
    ResponseType,
    Scope,
)


class TestEmail:
    """Tests for Email value object."""

    def test_valid_email(self):
        """Test valid email creation."""
        email = Email("test@example.com")
        assert email.value == "test@example.com"

    def test_email_normalization(self):
        """Test email is normalized to lowercase."""
        email = Email("Test@EXAMPLE.com")
        assert email.value == "test@example.com"

    def test_invalid_email_no_at(self):
        """Test email without @ is rejected."""
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("testexample.com")

    def test_invalid_email_no_domain(self):
        """Test email without domain is rejected."""
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("test@")

    def test_invalid_email_empty(self):
        """Test empty email is rejected."""
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("")

    def test_email_equality(self):
        """Test email equality comparison."""
        email1 = Email("test@example.com")
        email2 = Email("TEST@example.com")
        assert email1 == email2


class TestPassword:
    """Tests for Password value object."""

    def test_valid_password(self):
        """Test valid password creation."""
        password = Password("SecurePass123!")
        assert password.value == "SecurePass123!"

    def test_password_too_short(self):
        """Test password under minimum length is rejected."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            Password("Short1!")

    def test_password_no_uppercase(self):
        """Test password without uppercase is rejected."""
        with pytest.raises(ValueError, match="uppercase letter"):
            Password("securepass123!")

    def test_password_no_lowercase(self):
        """Test password without lowercase is rejected."""
        with pytest.raises(ValueError, match="lowercase letter"):
            Password("SECUREPASS123!")

    def test_password_no_digit(self):
        """Test password without digit is rejected."""
        with pytest.raises(ValueError, match="digit"):
            Password("SecurePassword!")

    def test_password_no_special(self):
        """Test password without special char is rejected."""
        with pytest.raises(ValueError, match="special character"):
            Password("SecurePass123")


class TestRedirectUri:
    """Tests for RedirectUri value object."""

    def test_valid_https_uri(self):
        """Test valid HTTPS URI."""
        uri = RedirectUri("https://example.com/callback")
        assert uri.value == "https://example.com/callback"

    def test_valid_localhost_http(self):
        """Test HTTP is allowed for localhost."""
        uri = RedirectUri("http://localhost:3000/callback")
        assert uri.value == "http://localhost:3000/callback"

    def test_valid_127_0_0_1_http(self):
        """Test HTTP is allowed for 127.0.0.1."""
        uri = RedirectUri("http://127.0.0.1:3000/callback")
        assert uri.value == "http://127.0.0.1:3000/callback"

    def test_invalid_http_non_localhost(self):
        """Test HTTP for non-localhost is rejected."""
        with pytest.raises(ValueError, match="must use HTTPS"):
            RedirectUri("http://example.com/callback")

    def test_invalid_fragment(self):
        """Test URI with fragment is rejected."""
        with pytest.raises(ValueError, match="must not contain fragments"):
            RedirectUri("https://example.com/callback#token=123")

    def test_matches_exact(self):
        """Test exact URI matching."""
        uri = RedirectUri("https://example.com/callback")
        assert uri.matches("https://example.com/callback")
        assert not uri.matches("https://example.com/other")


class TestCodeChallenge:
    """Tests for CodeChallenge value object."""

    def test_plain_challenge(self):
        """Test plain code challenge."""
        challenge = CodeChallenge("verifier123", "plain")
        assert challenge.verify("verifier123")
        assert not challenge.verify("wrong")

    def test_s256_challenge(self):
        """Test S256 code challenge."""
        # Pre-computed: base64url(sha256("verifier123"))
        import base64
        import hashlib
        
        verifier = "verifier123"
        digest = hashlib.sha256(verifier.encode()).digest()
        expected_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        
        challenge = CodeChallenge(expected_challenge, "S256")
        assert challenge.verify(verifier)
        assert not challenge.verify("wrong")

    def test_invalid_method(self):
        """Test invalid challenge method is rejected."""
        with pytest.raises(ValueError, match="Invalid code challenge method"):
            CodeChallenge("challenge", "invalid")


class TestEnums:
    """Tests for domain enums."""

    def test_grant_type_values(self):
        """Test grant type enum values."""
        assert GrantType.AUTHORIZATION_CODE.value == "authorization_code"
        assert GrantType.CLIENT_CREDENTIALS.value == "client_credentials"
        assert GrantType.REFRESH_TOKEN.value == "refresh_token"

    def test_response_type_values(self):
        """Test response type enum values."""
        assert ResponseType.CODE.value == "code"
        assert ResponseType.TOKEN.value == "token"

    def test_scope_values(self):
        """Test scope enum values."""
        assert Scope.OPENID.value == "openid"
        assert Scope.PROFILE.value == "profile"
        assert Scope.EMAIL.value == "email"
        assert Scope.OFFLINE_ACCESS.value == "offline_access"
