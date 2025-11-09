"""
Oracle router for GroundZero.

Routes claims to appropriate oracles based on domain classification.
"""

from server.oracles.null_oracle import NullOracle
from server.schemas.claim import Claim, DomainResult
from server.schemas.oracle_result import OracleResult, OracleRoutingDecision

PRIMARY_THRESHOLD = 0.6


class OracleRouter:
    """Routes claims to appropriate oracles based on domain."""

    def __init__(self):
        """Initialize the oracle router with oracle registry."""
        # Registry allows drop-in replacement in PR4/PR5/PR6
        self.null_oracle = NullOracle()
        self.registry = {
            "finance": self.null_oracle,  # TODO: replace in PR4
            "tech_release": self.null_oracle,  # TODO: replace in PR5
            "fallback": self.null_oracle,  # TODO: replace in PR6
        }

    def run(
        self, claim: Claim, domain: DomainResult
    ) -> tuple[list[OracleResult], OracleRoutingDecision]:
        """
        Route the claim to appropriate oracle(s) and return results.

        Args:
            claim: The parsed claim to analyze
            domain: The domain classification result

        Returns:
            Tuple of (oracle results list, routing decision)
        """
        # Choose primary oracle based on domain
        primary = domain.domain if domain.domain in ("finance", "tech_release") else "fallback"
        primary_oracle = self.registry.get(primary, self.null_oracle)

        results: list[OracleResult] = []
        primary_result = primary_oracle.analyze(claim, domain)
        results.append(primary_result)

        # Decide on fallback
        fallback_used = False
        if domain.confidence < PRIMARY_THRESHOLD:
            fallback_used = True
            fallback_oracle = self.registry.get("fallback", self.null_oracle)
            fallback_result = fallback_oracle.analyze(claim, domain)
            results.append(fallback_result)

        routing = OracleRoutingDecision(
            primary_oracle=(
                primary if primary in ("finance", "tech_release", "fallback") else "null"
            ),
            fallback_used=fallback_used,
        )
        return results, routing
