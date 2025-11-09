"""
Aggregate result schemas for combining multiple oracle results.

Defines models for aggregating oracle results using deterministic rules.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from server.schemas.oracle_result import EvidenceItem

if TYPE_CHECKING:
    from server.schemas.claim import Claim, DomainResult


class OracleCallResult(BaseModel):
    """Model representing the result from a single oracle call."""

    oracle_name: str = Field(..., description="Name of the oracle that was called")
    verdict: str = Field(..., description="Verdict from the oracle")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Evidence items")
    domain_context: dict = Field(default_factory=dict, description="Domain-specific context")


class AggregateResult(BaseModel):
    """Model representing the final aggregated result from multiple oracles."""

    final_verdict: str = Field(..., description="Final aggregated verdict")
    final_confidence: float = Field(..., ge=0.0, le=1.0, description="Final confidence score")
    oracle_calls: list[OracleCallResult] = Field(
        ..., description="List of individual oracle results"
    )
    domain: "DomainResult" = Field(..., description="Domain classification result")
    claim: "Claim" = Field(..., description="The original claim")
