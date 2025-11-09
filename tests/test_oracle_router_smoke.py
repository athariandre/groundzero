"""
Smoke tests for oracle router endpoint.
"""

from fastapi.testclient import TestClient

from server.main import app
from server.schemas.claim import Claim, DomainResult

client = TestClient(app)


class TestOracleRouterSmoke:
    """Smoke tests for /check_claim/oracles endpoint."""

    def test_run_oracles_finance_high_confidence(self):
        """Test oracle routing for finance domain with high confidence."""
        # Build test claim and domain
        claim = Claim(
            raw="AAPL rose 10% today",
            tickers=["AAPL"],
            companies=[],
            percentages=[10.0],
            date_hint="today",
            event_type="price_movement",
        )
        domain = DomainResult(domain="finance", confidence=0.9)

        # Make request
        response = client.post(
            "/check_claim/oracles",
            json={"claim": claim.model_dump(), "domain": domain.model_dump()},
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "results" in data
        assert "routing" in data

        # Check results
        results = data["results"]
        assert isinstance(results, list)
        assert len(results) >= 1  # At least one oracle result

        # Check first result
        first_result = results[0]
        assert "oracle_name" in first_result
        assert "verdict" in first_result
        assert "confidence" in first_result
        assert "evidence" in first_result
        assert first_result["verdict"] == "unsupported"  # NullOracle returns unsupported

        # Check routing
        routing = data["routing"]
        assert "primary_oracle" in routing
        assert "fallback_used" in routing
        assert routing["primary_oracle"] == "finance"
        assert routing["fallback_used"] is False  # High confidence, no fallback

    def test_run_oracles_tech_low_confidence(self):
        """Test oracle routing for tech_release domain with low confidence."""
        # Build test claim and domain
        claim = Claim(
            raw="Apple announced a new iPhone yesterday",
            tickers=[],
            companies=["Apple"],
            percentages=[],
            date_hint="yesterday",
            event_type="tech_release",
        )
        domain = DomainResult(domain="tech_release", confidence=0.5)

        # Make request
        response = client.post(
            "/check_claim/oracles",
            json={"claim": claim.model_dump(), "domain": domain.model_dump()},
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()

        # Check results - should have primary + fallback
        results = data["results"]
        assert len(results) == 2  # Primary + fallback due to low confidence

        # Check routing
        routing = data["routing"]
        assert routing["primary_oracle"] == "tech_release"
        assert routing["fallback_used"] is True  # Low confidence triggers fallback

    def test_run_oracles_general_domain(self):
        """Test oracle routing for general domain."""
        # Build test claim and domain
        claim = Claim(
            raw="This is a general statement",
            tickers=[],
            companies=[],
            percentages=[],
            date_hint=None,
            event_type=None,
        )
        domain = DomainResult(domain="general", confidence=0.8)

        # Make request
        response = client.post(
            "/check_claim/oracles",
            json={"claim": claim.model_dump(), "domain": domain.model_dump()},
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()

        # Check routing - should route to general (LLM oracle) for general domain
        routing = data["routing"]
        assert routing["primary_oracle"] == "general"
        assert routing["fallback_used"] is False  # High confidence, no additional fallback

    def test_run_oracles_missing_claim(self):
        """Test that missing claim returns error."""
        domain = DomainResult(domain="finance", confidence=0.9)

        response = client.post("/check_claim/oracles", json={"domain": domain.model_dump()})

        # Should return validation error
        assert response.status_code == 422

    def test_run_oracles_missing_domain(self):
        """Test that missing domain returns error."""
        claim = Claim(
            raw="AAPL rose 10% today",
            tickers=["AAPL"],
            companies=[],
            percentages=[10.0],
            date_hint="today",
            event_type="price_movement",
        )

        response = client.post("/check_claim/oracles", json={"claim": claim.model_dump()})

        # Should return validation error
        assert response.status_code == 422

    def test_run_oracles_response_structure(self):
        """Test that response has correct structure."""
        claim = Claim(
            raw="Test claim",
            tickers=[],
            companies=[],
            percentages=[],
            date_hint=None,
            event_type=None,
        )
        domain = DomainResult(domain="finance", confidence=0.7)

        response = client.post(
            "/check_claim/oracles",
            json={"claim": claim.model_dump(), "domain": domain.model_dump()},
        )

        assert response.status_code == 200
        data = response.json()

        # Check top-level structure
        assert "results" in data
        assert "routing" in data

        # Check result structure
        for result in data["results"]:
            assert "oracle_name" in result
            assert "verdict" in result
            assert "confidence" in result
            assert "evidence" in result
            assert "domain_context" in result

        # Check routing structure
        routing = data["routing"]
        assert "primary_oracle" in routing
        assert "fallback_used" in routing
