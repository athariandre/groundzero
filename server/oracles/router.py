"""
Oracle router for GroundZero.

Routes claims to appropriate oracles based on domain classification.
"""

from server.oracles.fallback import LLMOracle
from server.oracles.finance import FinanceOracle
from server.oracles.tech import TechReleaseOracle
from server.schemas.claim import Claim, DomainResult
from server.schemas.oracle_result import OracleResult, OracleRoutingDecision

PRIMARY_THRESHOLD = 0.6


class OracleRouter:
    """Routes claims to appropriate oracles based on domain."""

    def __init__(self):
        """Initialize the oracle router with oracle registry."""
        # Registry of domain-specific oracles
        self.finance_oracle = FinanceOracle()
        self.tech_release_oracle = TechReleaseOracle()
        self.llm_oracle = LLMOracle()

        self.registry = {
            "finance": self.finance_oracle,
            "tech_release": self.tech_release_oracle,
            "general": self.llm_oracle,
        }

    def run(
        self, claim: Claim, domain: DomainResult
    ) -> tuple[list[OracleResult], OracleRoutingDecision]:
        """
        Route the claim to appropriate oracle(s) and return results.

        Routing logic:
        - finance → FinanceOracle
        - tech_release → TechReleaseOracle
        - general → LLMOracle

        Fallback logic:
        - If domain.confidence < 0.6 → run LLMOracle as fallback
        - If primary oracle returns "uncertain" → run LLMOracle as fallback

        Args:
            claim: The parsed claim to analyze
            domain: The domain classification result

        Returns:
            Tuple of (oracle results list, routing decision)
        """
        # Choose primary oracle based on domain
        primary_domain = domain.domain if domain.domain in self.registry else "general"
        primary_oracle = self.registry[primary_domain]

        results: list[OracleResult] = []
        primary_result = primary_oracle.analyze(claim, domain)
        results.append(primary_result)

        # Decide on fallback
        fallback_used = False

        # Run LLM oracle as fallback if:
        # 1. Domain confidence is low (< 0.6)
        # 2. Primary oracle returned "uncertain"
        needs_fallback = (
            domain.confidence < PRIMARY_THRESHOLD or primary_result.verdict == "uncertain"
        )

        # Only run fallback if primary oracle is not already the LLM oracle
        if needs_fallback and primary_domain != "general":
            fallback_used = True
            fallback_result = self.llm_oracle.analyze(claim, domain)
            results.append(fallback_result)

        routing = OracleRoutingDecision(
            primary_oracle=primary_domain,
            fallback_used=fallback_used,
        )
        return results, routing
