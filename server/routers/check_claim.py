"""
Check claim API router.

Endpoints for parsing and classifying claims.
"""

import logging

from fastapi import APIRouter, HTTPException

from server.ml.claim_extractor import extract_claim
from server.ml.domain_classifier import classify_domain
from server.oracles.aggregator import aggregate_oracle_results
from server.oracles.router import OracleRouter
from server.schemas.aggregate_result import AggregateResult
from server.schemas.claim import Claim, DomainResult, ParseClaimRequest, ParseClaimResponse

router = APIRouter(prefix="/check_claim", tags=["check_claim"])
logger = logging.getLogger(__name__)

# Initialize the oracle router
_oracle_router = OracleRouter()


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

    # Classify domain
    domain = classify_domain(request.claim_text, claim)
    logger.debug(f"Domain classified as: {domain}")

    return ParseClaimResponse(claim=claim, domain=domain)


@router.post("/check", response_model=AggregateResult)
async def check_claim(request: ParseClaimRequest) -> AggregateResult:
    """
    Parse, classify, and fact-check a claim using oracle routing and aggregation.
    
    This endpoint provides a complete fact-checking pipeline:
    1. Parse the claim to extract structured information
    2. Classify the claim's domain (finance, tech_release, general)
    3. Route to appropriate oracle(s) based on domain and confidence
    4. Aggregate results from multiple oracles into a final verdict
    
    Args:
        request: ParseClaimRequest containing the claim text
        
    Returns:
        AggregateResult with final verdict, confidence, and supporting evidence
    """
    # Validate input
    if not request.claim_text.strip():
        raise HTTPException(status_code=400, detail="Claim text cannot be empty.")
    
    logger.info(f"Checking claim: {request.claim_text[:80]}")
    
    # Step 1: Parse claim
    claim = extract_claim(request.claim_text)
    logger.debug(f"Extracted: {claim.model_dump()}")
    
    # Step 2: Classify domain
    domain = classify_domain(request.claim_text, claim)
    logger.debug(f"Domain classified as: {domain}")
    
    # Step 3: Route to oracle(s)
    oracle_results, routing = _oracle_router.run(claim, domain)
    logger.debug(f"Oracle routing: {routing.model_dump()}")
    logger.debug(f"Oracle results: {[r.oracle_name for r in oracle_results]}")
    
    # Step 4: Aggregate results
    aggregate_result = aggregate_oracle_results(oracle_results, claim, domain)
    logger.info(f"Final verdict: {aggregate_result.final_verdict} (confidence: {aggregate_result.final_confidence:.2f})")
    
    return aggregate_result
