"""
LLM Oracle stub for GroundZero.

Placeholder implementation that returns 'uncertain' until full implementation.
This oracle serves as a fallback for low-confidence domain classifications.
"""

from server.oracles.base import Oracle
from server.schemas.claim import Claim, DomainResult
from server.schemas.oracle_result import OracleResult


class LLMOracle(Oracle):
    """Stub oracle for LLM-based fact checking."""

    name = "llm_oracle"

    def analyze(self, claim: Claim, domain: DomainResult) -> OracleResult:
        """
        Stub implementation that returns uncertain.

        Args:
            claim: The parsed claim to analyze
            domain: The domain classification result

        Returns:
            OracleResult with 'uncertain' verdict
        """
        return OracleResult(
            oracle_name=self.name,
            verdict="uncertain",
            confidence=0.3,
            evidence=[],
            domain_context={"reason": "LLM oracle not yet implemented"},
        )
