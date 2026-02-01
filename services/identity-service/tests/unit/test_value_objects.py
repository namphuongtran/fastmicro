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

    def test_email_case_preserved(self):
        """Test email value is preserved as provided."""
        email = Email("Test@EXAMPLE.com")
        assert email.value == "Test@EXAMPLE.com"

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
        email2 = Email("test@example.com")
        assert email1 == email2
        # Different case emails are not equal (no normalization)
        email3 = Email("TEST@example.com")
        assert email1 != email3


class TestPassword:
    """Tests for Password value object."""

    def test_valid_password(self):
        """Test valid password creation using validate."""
        password = Password.validate("SecurePass123!")
        assert password.value == "SecurePass123!"

    def test_raw_password_creation(self):
        """Test raw password creation without validation."""
        password = Password("anypassword")
        assert password.value == "anypassword"

    def test_password_too_short(self):
        """Test password under minimum length is rejected."""
        with pytest.raises(ValueError, match="at least 12 characters"):
            Password.validate("Short1!")

    def test_password_no_uppercase(self):
        """Test password without uppercase is rejected."""
        with pytest.raises(ValueError, match="uppercase letter"):
            Password.validate("securepassword123!")

    def test_password_no_lowercase(self):
        """Test password without lowercase is rejected."""
        with pytest.raises(ValueError, match="lowercase letter"):
            Password.validate("SECUREPASSWORD123!")

    def test_password_no_digit(self):
        """Test password without digit is rejected."""
        with pytest.raises(ValueError, match="digit"):
            Password.validate("SecurePassword!!")

    def test_password_no_special(self):
        """Test password without special char is rejected."""
        with pytest.raises(ValueError, match="special character"):
            Password.validate("SecurePassword123")


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
        """Test plain code challenge creation."""
        # Must be 43-128 characters for valid PKCE
        verifier = "a" * 43  # minimum length
        challenge = CodeChallenge(verifier, "plain")
        assert challenge.value == verifier
        assert challenge.method == "plain"

    def test_s256_challenge(self):
        """Test S256 code challenge."""
        import base64
        import hashlib

        verifier = "my_code_verifier_123456789012345678901234567890"
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge_value = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

        challenge = CodeChallenge(challenge_value, "S256")
        assert challenge.value == challenge_value
        assert challenge.method == "S256"

    def test_invalid_method(self):
        """Test invalid challenge method is rejected."""
        with pytest.raises(ValueError, match="must be"):
            CodeChallenge("a" * 43, "invalid")

    def test_challenge_too_short(self):
        """Test challenge under minimum length is rejected."""
        with pytest.raises(ValueError, match="between 43 and 128"):
            CodeChallenge("tooshort", "S256")

    def test_challenge_too_long(self):
        """Test challenge over maximum length is rejected."""
        with pytest.raises(ValueError, match="between 43 and 128"):
            CodeChallenge("a" * 130, "S256")


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
