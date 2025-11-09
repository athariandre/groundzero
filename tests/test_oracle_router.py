"""
Tests for enhanced oracle router with fallback logic.
"""

import pytest

from server.oracles.router import OracleRouter
from server.schemas.claim import Claim, DomainResult


class TestOracleRouter:
    """Test cases for oracle routing logic."""

    def test_route_to_finance_oracle_high_confidence(self):
        """Test routing to finance oracle with high confidence."""
        router = OracleRouter()
        claim = Claim(
            raw="AAPL rose 10% today",
            tickers=["AAPL"],
            percentages=[10.0],
            date_hint="today",
        )
        domain = DomainResult(domain="finance", confidence=0.9)
        
        results, routing = router.run(claim, domain)
        
        # Should route to finance oracle only (no fallback due to high confidence)
        assert routing.primary_oracle == "finance"
        assert routing.fallback_used is False
        assert len(results) == 1
        assert results[0].oracle_name == "finance"

    def test_route_to_tech_release_oracle(self):
        """Test routing to tech release oracle."""
        router = OracleRouter()
        claim = Claim(
            raw="Apple announced new iPhone",
            companies=["Apple"],
            event_type="tech_release",
        )
        domain = DomainResult(domain="tech_release", confidence=0.85)
        
        results, routing = router.run(claim, domain)
        
        assert routing.primary_oracle == "tech_release"
        # Tech release oracle stub returns "uncertain", so fallback should be used
        assert routing.fallback_used is True
        assert len(results) == 2  # Primary + fallback
        assert results[0].oracle_name == "tech_release"
        assert results[1].oracle_name == "llm_oracle"

    def test_route_to_general_llm_oracle(self):
        """Test routing to general LLM oracle."""
        router = OracleRouter()
        claim = Claim(raw="This is a general statement")
        domain = DomainResult(domain="general", confidence=0.8)
        
        results, routing = router.run(claim, domain)
        
        assert routing.primary_oracle == "general"
        assert routing.fallback_used is False
        assert len(results) == 1
        assert results[0].oracle_name == "llm_oracle"

    def test_fallback_on_low_confidence(self):
        """Test that LLM oracle is used as fallback when domain confidence < 0.6."""
        router = OracleRouter()
        claim = Claim(
            raw="AAPL might have moved",
            tickers=["AAPL"],
        )
        domain = DomainResult(domain="finance", confidence=0.5)
        
        results, routing = router.run(claim, domain)
        
        # Should use fallback due to low confidence
        assert routing.primary_oracle == "finance"
        assert routing.fallback_used is True
        assert len(results) == 2
        assert results[0].oracle_name == "finance"
        assert results[1].oracle_name == "llm_oracle"

    def test_fallback_on_uncertain_verdict(self):
        """Test that LLM oracle is used as fallback when primary oracle returns uncertain."""
        router = OracleRouter()
        # Tech release oracle stub always returns uncertain
        claim = Claim(
            raw="Apple announced something",
            companies=["Apple"],
        )
        domain = DomainResult(domain="tech_release", confidence=0.9)
        
        results, routing = router.run(claim, domain)
        
        # Should use fallback because tech_release oracle returns uncertain
        assert routing.primary_oracle == "tech_release"
        assert routing.fallback_used is True
        assert len(results) == 2
        assert results[0].oracle_name == "tech_release"
        assert results[0].verdict == "uncertain"
        assert results[1].oracle_name == "llm_oracle"

    def test_no_fallback_for_general_domain(self):
        """Test that general domain doesn't trigger fallback to itself."""
        router = OracleRouter()
        claim = Claim(raw="Random statement")
        domain = DomainResult(domain="general", confidence=0.3)
        
        results, routing = router.run(claim, domain)
        
        # Low confidence but primary is already LLM, no fallback
        assert routing.primary_oracle == "general"
        assert routing.fallback_used is False
        assert len(results) == 1
        assert results[0].oracle_name == "llm_oracle"

    def test_confidence_threshold_boundary(self):
        """Test behavior at confidence threshold boundary (0.6)."""
        router = OracleRouter()
        claim = Claim(raw="Test claim", tickers=["AAPL"])
        
        # At threshold (0.6), should NOT use fallback
        domain_at_threshold = DomainResult(domain="finance", confidence=0.6)
        results, routing = router.run(claim, domain_at_threshold)
        assert routing.fallback_used is False
        assert len(results) == 1
        
        # Just below threshold (0.59), should use fallback
        domain_below_threshold = DomainResult(domain="finance", confidence=0.59)
        results, routing = router.run(claim, domain_below_threshold)
        assert routing.fallback_used is True
        assert len(results) == 2

    def test_unknown_domain_routes_to_general(self):
        """Test that unknown domains route to general (LLM) oracle."""
        router = OracleRouter()
        claim = Claim(raw="Some claim")
        # Use an unknown domain (should fall back to general)
        domain = DomainResult(domain="unknown_domain", confidence=0.8)
        
        results, routing = router.run(claim, domain)
        
        assert routing.primary_oracle == "general"
        assert len(results) == 1
        assert results[0].oracle_name == "llm_oracle"

    def test_oracle_registry_contains_all_domains(self):
        """Test that oracle registry has entries for all expected domains."""
        router = OracleRouter()
        
        assert "finance" in router.registry
        assert "tech_release" in router.registry
        assert "general" in router.registry
        
        # Verify oracle types
        assert router.registry["finance"].name == "finance"
        assert router.registry["tech_release"].name == "tech_release"
        assert router.registry["general"].name == "llm_oracle"
