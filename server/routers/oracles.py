"""
Oracle API router.

Endpoints for running oracles on parsed claims.
"""

from fastapi import APIRouter, HTTPException

from server.oracles.router import OracleRouter
from server.schemas.claim import Claim, DomainResult  # noqa: F401
from server.schemas.oracle_result import RunOraclesRequest, RunOraclesResponse

# Rebuild RunOraclesRequest to resolve forward references
RunOraclesRequest.model_rebuild()

router = APIRouter(prefix="/check_claim", tags=["check_claim"])
_oracle_router = OracleRouter()


@router.post("/oracles", response_model=RunOraclesResponse)
async def run_oracles(req: RunOraclesRequest) -> RunOraclesResponse:
    """
    Route the parsed claim/domain to the appropriate oracle(s).

    Returns structured results plus routing metadata.

    Args:
        req: RunOraclesRequest containing claim and domain

    Returns:
        RunOraclesResponse with oracle results and routing decision
    """
    if not req.claim or not req.domain:
        raise HTTPException(status_code=400, detail="Missing claim or domain")
    results, routing = _oracle_router.run(req.claim, req.domain)
    return RunOraclesResponse(results=results, routing=routing)
