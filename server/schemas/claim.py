"""
Claim-related Pydantic models for the GroundZero API.
"""

from typing import Optional

from pydantic import BaseModel, Field


class Claim(BaseModel):
    """Model representing an extracted claim with metadata."""

    raw: str = Field(..., description="Original raw text of the claim")
    tickers: list[str] = Field(
        default_factory=list, description="List of extracted stock tickers (e.g., AAPL, TSLA)"
    )
    companies: list[str] = Field(
        default_factory=list, description="List of extracted company names"
    )
    percentages: list[float] = Field(
        default_factory=list, description="List of extracted percentage values"
    )
    date_hint: Optional[str] = Field(
        None, description="Detected date hint (e.g., 'today', 'yesterday')"
    )
    event_type: Optional[str] = Field(
        None, description="Detected event type (e.g., 'price_movement', 'tech_release')"
    )


class DomainResult(BaseModel):
    """Model representing the domain classification result."""

    domain: str = Field(..., description="Classified domain (finance, tech_release, general)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")


class ParseClaimRequest(BaseModel):
    """Request model for the /check_claim/parse endpoint."""

    claim_text: str = Field(..., description="The claim text to parse and classify")


class ParseClaimResponse(BaseModel):
    """Response model for the /check_claim/parse endpoint."""

    claim: Claim = Field(..., description="Extracted claim information")
    domain: DomainResult = Field(..., description="Domain classification result")
