"""
Check claim API router.

Endpoints for parsing and classifying claims.
"""

import logging
import os

from fastapi import APIRouter, HTTPException

from server.ml.claim_extractor import extract_claim
from server.ml.domain_classifier import classify_domain
from server.schemas.claim import ParseClaimRequest, ParseClaimResponse

router = APIRouter(prefix="/check_claim", tags=["check_claim"])
logger = logging.getLogger(__name__)


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
    # Validate input
    if not request.claim_text.strip():
        raise HTTPException(status_code=400, detail="Claim text cannot be empty.")

    logger.info(f"Received claim: {request.claim_text[:80]}")

    # Extract claim information
    claim = extract_claim(request.claim_text)
    logger.debug(f"Extracted: {claim.model_dump()}")

    # Classify domain - use environment variable to control LLM usage
    use_llm = os.getenv("USE_LLM", "true").lower() == "true"
    domain = classify_domain(request.claim_text, claim, use_llm=use_llm)
    logger.debug(f"Domain classified as: {domain}")

    return ParseClaimResponse(claim=claim, domain=domain)
