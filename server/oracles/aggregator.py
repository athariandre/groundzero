"""
Oracle result aggregation logic.

Combines multiple oracle results using deterministic rules.
"""

from server.schemas.aggregate_result import AggregateResult, OracleCallResult
from server.schemas.claim import Claim, DomainResult
from server.schemas.oracle_result import OracleResult


def aggregate_oracle_results(
    oracle_results: list[OracleResult],
    claim: Claim,
    domain: DomainResult,
) -> AggregateResult:
    """
    Aggregate multiple oracle results into a final verdict using deterministic rules.
    
    Aggregation Rules:
    1. If any oracle verdict == "likely_false": final = likely_false
    2. Else if any oracle verdict == "likely_true": final = likely_true
    3. Else: final = uncertain
    
    Confidence:
    - If mix of true/false: choose the lowest confidence
    - If supporting (all true-ish): average the confidences
    - If all uncertain: use 0.3
    
    Args:
        oracle_results: List of OracleResult objects from different oracles
        claim: The original claim
        domain: The domain classification result
        
    Returns:
        AggregateResult with final verdict and confidence
    """
    # Convert OracleResult to OracleCallResult
    oracle_calls = [
        OracleCallResult(
            oracle_name=result.oracle_name,
            verdict=result.verdict,
            confidence=result.confidence,
            evidence=result.evidence,
            domain_context=result.domain_context or {},
        )
        for result in oracle_results
    ]
    
    # Extract verdicts and confidences
    verdicts = [result.verdict for result in oracle_results]
    confidences = [result.confidence for result in oracle_results]
    
    # Apply deterministic aggregation rules
    final_verdict = "uncertain"
    final_confidence = 0.3
    
    # Rule 1: If any oracle verdict == "likely_false", final = likely_false
    if "likely_false" in verdicts:
        final_verdict = "likely_false"
        # For mixed verdicts (true/false), choose the lowest confidence
        if "likely_true" in verdicts:
            final_confidence = min(confidences)
        else:
            # All are likely_false or uncertain/unsupported
            false_confidences = [
                c for v, c in zip(verdicts, confidences) 
                if v == "likely_false"
            ]
            final_confidence = sum(false_confidences) / len(false_confidences) if false_confidences else 0.3
    
    # Rule 2: Else if any oracle verdict == "likely_true", final = likely_true
    elif "likely_true" in verdicts:
        final_verdict = "likely_true"
        # All supporting (true-ish), average the confidences
        true_confidences = [
            c for v, c in zip(verdicts, confidences) 
            if v == "likely_true"
        ]
        final_confidence = sum(true_confidences) / len(true_confidences) if true_confidences else 0.3
    
    # Rule 3: Else (all uncertain/unsupported), final = uncertain
    else:
        final_verdict = "uncertain"
        final_confidence = 0.3
    
    return AggregateResult(
        final_verdict=final_verdict,
        final_confidence=final_confidence,
        oracle_calls=oracle_calls,
        domain=domain,
        claim=claim,
    )
