"""
Null oracle implementation.

Returns an 'unsupported' verdict for all claims.
Used as a placeholder until domain-specific oracles are implemented.
"""

from server.oracles.base import Oracle
from server.schemas.claim import Claim, DomainResult
from server.schemas.oracle_result import OracleResult


class NullOracle(Oracle):
    """Oracle that returns 'unsupported' for all claims."""

    name = "null"

    def analyze(self, claim: Claim, domain: DomainResult) -> OracleResult:
        """
        Return an unsupported result.

        Args:
            claim: The parsed claim to analyze
            domain: The domain classification result

        Returns:
            OracleResult with 'unsupported' verdict
        """
        return OracleResult(
            oracle_name=self.name,
            verdict="unsupported",
            confidence=0.0,
            evidence=[],
            domain_context={"reason": "No domain-specific oracle implemented yet"},
        )
