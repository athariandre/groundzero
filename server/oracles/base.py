"""
Base oracle interface for GroundZero.

Defines the abstract interface that all oracles must implement.
"""

from abc import ABC, abstractmethod

from server.schemas.claim import Claim, DomainResult
from server.schemas.oracle_result import OracleResult


class Oracle(ABC):
    """Abstract base class for all oracles."""

    name: str

    @abstractmethod
    def analyze(self, claim: Claim, domain: DomainResult) -> OracleResult:
        """
        Run the oracle for the given claim/domain and return a structured OracleResult.

        Implementations MUST NOT throw; return 'unsupported' if not applicable.

        Args:
            claim: The parsed claim to analyze
            domain: The domain classification result

        Returns:
            OracleResult with verdict, confidence, and evidence
        """
        ...
