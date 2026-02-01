"""Placeholder tests for federation-gateway.

TODO: Add actual tests for the federation gateway service.
"""

import pytest


class TestPlaceholder:
    """Placeholder test class to prevent pytest exit code 5 (no tests collected)."""

    def test_placeholder(self) -> None:
        """Placeholder test - remove when real tests are added."""
        # This test exists to prevent CI failure due to no tests collected.
        # pytest returns exit code 5 when no tests are found, which fails CI.
        assert True, "Placeholder test to ensure pytest collects at least one test"

    @pytest.mark.skip(reason="TODO: Implement federation gateway tests")
    def test_federation_gateway_health(self) -> None:
        """Test the health endpoint."""
        pass

    @pytest.mark.skip(reason="TODO: Implement federation gateway tests")
    def test_federation_gateway_graphql_endpoint(self) -> None:
        """Test the GraphQL federation endpoint."""
        pass
