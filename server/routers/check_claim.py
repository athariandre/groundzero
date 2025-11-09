"""
Check claim API router.

Endpoints for parsing and classifying claims.
"""

from fastapi import APIRouter

from server.ml.claim_extractor import extract_claim
from server.ml.domain_classifier import classify_domain
from server.schemas.claim import ParseClaimRequest, ParseClaimResponse

router = APIRouter(prefix="/check_claim", tags=["check_claim"])


@router.post("/parse", response_model=ParseClaimResponse)
async def parse_claim(request: ParseClaimRequest) -> ParseClaimResponse:
    """
    Parse and classify a claim.

    Extracts structured information from the claim text and classifies it
    into a domain (finance, tech_release, or general).

    Args:
        request: ParseClaimRequest containing the claim text

    Returns:
        ParseClaimResponse with extracted claim and domain classification
    """
    # Extract claim information
    claim = extract_claim(request.claim_text)

    # Classify domain
    domain = classify_domain(request.claim_text, claim, use_llm=True)

    return ParseClaimResponse(claim=claim, domain=domain)
