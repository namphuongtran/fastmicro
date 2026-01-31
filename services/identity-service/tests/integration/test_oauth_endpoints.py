"""Integration tests for OAuth2/OIDC endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client: TestClient):
        """Test /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_readiness_check(self, client: TestClient):
        """Test /ready endpoint."""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_liveness_check(self, client: TestClient):
        """Test /live endpoint."""
        response = client.get("/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestDiscoveryEndpoints:
    """Tests for OIDC discovery endpoints."""

    def test_openid_configuration(self, client: TestClient):
        """Test /.well-known/openid-configuration endpoint."""
        response = client.get("/.well-known/openid-configuration")
        assert response.status_code == 200
        
        data = response.json()
        assert "issuer" in data
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "userinfo_endpoint" in data
        assert "jwks_uri" in data
        assert "revocation_endpoint" in data
        assert "introspection_endpoint" in data
        
        # Check supported features
        assert "authorization_code" in data["grant_types_supported"]
        assert "code" in data["response_types_supported"]
        assert "openid" in data["scopes_supported"]
        
        # Check security features
        assert "S256" in data["code_challenge_methods_supported"]

    def test_jwks_endpoint(self, client: TestClient):
        """Test /.well-known/jwks.json endpoint."""
        response = client.get("/.well-known/jwks.json")
        assert response.status_code == 200
        
        data = response.json()
        assert "keys" in data
        assert len(data["keys"]) > 0
        
        key = data["keys"][0]
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert "kid" in key
        assert "n" in key
        assert "e" in key


class TestAuthorizationEndpoint:
    """Tests for authorization endpoint."""

    def test_authorize_missing_client_id(self, client: TestClient):
        """Test authorization without client_id."""
        response = client.get("/oauth2/authorize", follow_redirects=False)
        # Should return error (redirect or JSON)
        assert response.status_code in [400, 302]

    def test_authorize_invalid_client(self, client: TestClient):
        """Test authorization with invalid client."""
        response = client.get(
            "/oauth2/authorize",
            params={
                "response_type": "code",
                "client_id": "invalid-client",
                "redirect_uri": "https://example.com/callback",
                "scope": "openid",
            },
            follow_redirects=False,
        )
        # Should return error
        assert response.status_code in [400, 302]


class TestTokenEndpoint:
    """Tests for token endpoint."""

    def test_token_missing_grant_type(self, client: TestClient):
        """Test token request without grant_type."""
        response = client.post("/oauth2/token", data={})
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_request"

    def test_token_unsupported_grant_type(self, client: TestClient):
        """Test token request with unsupported grant type."""
        response = client.post(
            "/oauth2/token",
            data={"grant_type": "password"},  # Not supported
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"] in ["invalid_request", "unsupported_grant_type"]

    def test_token_invalid_authorization_code(self, client: TestClient):
        """Test token exchange with invalid code."""
        response = client.post(
            "/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": "invalid-code",
                "client_id": "test-client",
                "redirect_uri": "https://example.com/callback",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"] in ["invalid_grant", "invalid_request"]


class TestIntrospectionEndpoint:
    """Tests for token introspection endpoint."""

    def test_introspect_missing_token(self, client: TestClient):
        """Test introspection without token."""
        response = client.post("/oauth2/introspect", data={})
        assert response.status_code == 400

    def test_introspect_invalid_token(self, client: TestClient):
        """Test introspection with invalid token."""
        response = client.post(
            "/oauth2/introspect",
            data={"token": "invalid-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False


class TestRevocationEndpoint:
    """Tests for token revocation endpoint."""

    def test_revoke_missing_token(self, client: TestClient):
        """Test revocation without token."""
        response = client.post("/oauth2/revoke", data={})
        assert response.status_code == 400

    def test_revoke_invalid_token(self, client: TestClient):
        """Test revocation with invalid token succeeds (per RFC 7009)."""
        response = client.post(
            "/oauth2/revoke",
            data={"token": "invalid-token"},
        )
        # Per RFC 7009, revocation of invalid tokens should succeed
        assert response.status_code == 200


class TestUserInfoEndpoint:
    """Tests for userinfo endpoint."""

    def test_userinfo_no_auth(self, client: TestClient):
        """Test userinfo without authorization."""
        response = client.get("/oauth2/userinfo")
        assert response.status_code == 401

    def test_userinfo_invalid_token(self, client: TestClient):
        """Test userinfo with invalid token."""
        response = client.get(
            "/oauth2/userinfo",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401
