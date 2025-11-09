"""
Tech Release Oracle stub for GroundZero.

Placeholder implementation that returns 'uncertain' until full implementation.
"""

from server.oracles.base import Oracle
from server.schemas.claim import Claim, DomainResult
from server.schemas.oracle_result import OracleResult


class TechReleaseOracle(Oracle):
    """Stub oracle for tech release claims."""

    name = "tech_release"

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
            domain_context={"reason": "Tech release oracle not yet implemented"},
        )
