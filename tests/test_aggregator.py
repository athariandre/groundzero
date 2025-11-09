"""
Tests for oracle result aggregation logic.
"""

import pytest

from server.oracles.aggregator import aggregate_oracle_results
from server.schemas.claim import Claim, DomainResult
from server.schemas.oracle_result import OracleResult


class TestAggregator:
    """Test cases for oracle result aggregation."""

    def test_aggregate_single_likely_true(self):
        """Test aggregation with single likely_true result."""
        claim = Claim(raw="Test claim", tickers=["AAPL"])
        domain = DomainResult(domain="finance", confidence=0.9)

        oracle_results = [
            OracleResult(
                oracle_name="finance",
                verdict="likely_true",
                confidence=0.85,
                evidence=[],
            )
        ]

        result = aggregate_oracle_results(oracle_results, claim, domain)

        assert result.final_verdict == "likely_true"
        assert result.final_confidence == 0.85
        assert len(result.oracle_calls) == 1
        assert result.claim == claim
        assert result.domain == domain

    def test_aggregate_single_likely_false(self):
        """Test aggregation with single likely_false result."""
        claim = Claim(raw="Test claim", tickers=["AAPL"])
        domain = DomainResult(domain="finance", confidence=0.9)

        oracle_results = [
            OracleResult(
                oracle_name="finance",
                verdict="likely_false",
                confidence=0.75,
                evidence=[],
            )
        ]

        result = aggregate_oracle_results(oracle_results, claim, domain)

        assert result.final_verdict == "likely_false"
        assert result.final_confidence == 0.75

    def test_aggregate_single_uncertain(self):
        """Test aggregation with single uncertain result."""
        claim = Claim(raw="Test claim", tickers=[])
        domain = DomainResult(domain="general", confidence=0.8)

        oracle_results = [
            OracleResult(
                oracle_name="llm_oracle",
                verdict="uncertain",
                confidence=0.3,
                evidence=[],
            )
        ]

        result = aggregate_oracle_results(oracle_results, claim, domain)

        assert result.final_verdict == "uncertain"
        assert result.final_confidence == 0.3

    def test_aggregate_likely_false_wins_over_likely_true(self):
        """Test that likely_false takes precedence over likely_true."""
        claim = Claim(raw="Test claim", tickers=["AAPL"])
        domain = DomainResult(domain="finance", confidence=0.5)

        oracle_results = [
            OracleResult(
                oracle_name="finance",
                verdict="likely_true",
                confidence=0.8,
                evidence=[],
            ),
            OracleResult(
                oracle_name="llm_oracle",
                verdict="likely_false",
                confidence=0.7,
                evidence=[],
            ),
        ]

        result = aggregate_oracle_results(oracle_results, claim, domain)

        # Rule 1: likely_false takes precedence
        assert result.final_verdict == "likely_false"
        # Mixed verdicts: choose lowest confidence
        assert result.final_confidence == 0.7

    def test_aggregate_multiple_likely_true(self):
        """Test aggregation with multiple likely_true results."""
        claim = Claim(raw="Test claim", tickers=["AAPL"])
        domain = DomainResult(domain="finance", confidence=0.5)

        oracle_results = [
            OracleResult(
                oracle_name="finance",
                verdict="likely_true",
                confidence=0.8,
                evidence=[],
            ),
            OracleResult(
                oracle_name="llm_oracle",
                verdict="likely_true",
                confidence=0.6,
                evidence=[],
            ),
        ]

        result = aggregate_oracle_results(oracle_results, claim, domain)

        assert result.final_verdict == "likely_true"
        # Supporting verdicts: average the confidences
        assert result.final_confidence == pytest.approx(0.7)

    def test_aggregate_multiple_likely_false(self):
        """Test aggregation with multiple likely_false results."""
        claim = Claim(raw="Test claim", tickers=["AAPL"])
        domain = DomainResult(domain="finance", confidence=0.5)

        oracle_results = [
            OracleResult(
                oracle_name="finance",
                verdict="likely_false",
                confidence=0.9,
                evidence=[],
            ),
            OracleResult(
                oracle_name="llm_oracle",
                verdict="likely_false",
                confidence=0.7,
                evidence=[],
            ),
        ]

        result = aggregate_oracle_results(oracle_results, claim, domain)

        assert result.final_verdict == "likely_false"
        # Multiple likely_false: average them
        assert result.final_confidence == pytest.approx(0.8)

    def test_aggregate_all_uncertain(self):
        """Test aggregation when all results are uncertain."""
        claim = Claim(raw="Test claim", tickers=[])
        domain = DomainResult(domain="general", confidence=0.4)

        oracle_results = [
            OracleResult(
                oracle_name="tech_release",
                verdict="uncertain",
                confidence=0.3,
                evidence=[],
            ),
            OracleResult(
                oracle_name="llm_oracle",
                verdict="uncertain",
                confidence=0.3,
                evidence=[],
            ),
        ]

        result = aggregate_oracle_results(oracle_results, claim, domain)

        assert result.final_verdict == "uncertain"
        # All uncertain: use 0.3
        assert result.final_confidence == 0.3

    def test_aggregate_uncertain_with_unsupported(self):
        """Test aggregation with uncertain and unsupported results."""
        claim = Claim(raw="Test claim", tickers=[])
        domain = DomainResult(domain="general", confidence=0.8)

        oracle_results = [
            OracleResult(
                oracle_name="finance",
                verdict="unsupported",
                confidence=0.0,
                evidence=[],
            ),
            OracleResult(
                oracle_name="llm_oracle",
                verdict="uncertain",
                confidence=0.3,
                evidence=[],
            ),
        ]

        result = aggregate_oracle_results(oracle_results, claim, domain)

        # No likely_true or likely_false, so uncertain
        assert result.final_verdict == "uncertain"
        assert result.final_confidence == 0.3

    def test_aggregate_preserves_oracle_calls(self):
        """Test that oracle call results are properly converted and preserved."""
        claim = Claim(raw="Test claim", tickers=["AAPL"])
        domain = DomainResult(domain="finance", confidence=0.9)

        oracle_results = [
            OracleResult(
                oracle_name="finance",
                verdict="likely_true",
                confidence=0.85,
                evidence=[],
                domain_context={"ticker": "AAPL"},
            ),
            OracleResult(
                oracle_name="llm_oracle",
                verdict="likely_true",
                confidence=0.75,
                evidence=[],
                domain_context={"method": "llm"},
            ),
        ]

        result = aggregate_oracle_results(oracle_results, claim, domain)

        assert len(result.oracle_calls) == 2

        # Check first oracle call
        call1 = result.oracle_calls[0]
        assert call1.oracle_name == "finance"
        assert call1.verdict == "likely_true"
        assert call1.confidence == 0.85
        assert call1.domain_context == {"ticker": "AAPL"}

        # Check second oracle call
        call2 = result.oracle_calls[1]
        assert call2.oracle_name == "llm_oracle"
        assert call2.verdict == "likely_true"
        assert call2.confidence == 0.75
        assert call2.domain_context == {"method": "llm"}
