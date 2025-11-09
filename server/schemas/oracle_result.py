"""
Oracle result schemas for GroundZero API.

Defines models for oracle-based fact checking results.
"""

from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from server.schemas.claim import Claim, DomainResult


class EvidenceItem(BaseModel):
    """Model representing a piece of evidence from an oracle."""

    source: str = Field(..., description="Source name or type (e.g., 'Company Blog', 'EDGAR')")
    title: Optional[str] = Field(None, description="Title or short label for the evidence")
    url: Optional[str] = Field(None, description="Canonical URL to the evidence, if any")
    published_at: Optional[str] = Field(None, description="ISO datetime string")
    stance: Optional[Literal["supports", "refutes", "unrelated"]] = None
    stance_conf: Optional[float] = Field(None, ge=0.0, le=1.0)
    extract: Optional[str] = Field(None, description="Short relevant excerpt")


class OracleResult(BaseModel):
    """Model representing the result from an oracle."""

    oracle_name: str = Field(
        ...,
        description=(
            "Identifier for the oracle (e.g., 'finance', 'tech_release', 'fallback', 'null')"
        ),
    )
    verdict: Literal["likely_true", "likely_false", "uncertain", "unsupported"] = "unsupported"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    domain_context: Optional[dict] = Field(
        default=None, description="Domain-specific metrics/context"
    )


class OracleRoutingDecision(BaseModel):
    """Model representing the routing decision made by the oracle router."""

    primary_oracle: Literal["finance", "tech_release", "general"]
    fallback_used: bool = False


class RunOraclesRequest(BaseModel):
    """Request model for running oracles on a claim."""

    claim: "Claim"
    domain: "DomainResult"


class RunOraclesResponse(BaseModel):
    """Response model for oracle results."""

    results: list[OracleResult]
    routing: OracleRoutingDecision
