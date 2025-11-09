"""
Domain classification module for categorizing claims into domains.
"""

import os
import re
from typing import Optional

from server.schemas.claim import Claim, DomainResult

# Finance-related keywords
FINANCE_KEYWORDS = [
    "rose",
    "fell",
    "jumped",
    "surged",
    "dumped",
    "pumped",
    "price",
    "stock",
    "trading",
]

# Tech release keywords
TECH_RELEASE_KEYWORDS = ["announced", "released", "launched", "introduced"]


class DomainClassifier:
    """Classifies claims into domains using rule-based and LLM fallback approaches."""

    def __init__(self, use_llm: bool = True):
        """
        Initialize the domain classifier.

        Args:
            use_llm: Whether to use LLM fallback for unclear cases
        """
        self.use_llm = use_llm
        self._llm_client = None

    def _init_llm_client(self):
        """Initialize OpenAI client for LLM fallback if not already initialized."""
        if self._llm_client is None and self.use_llm:
            try:
                from openai import OpenAI

                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self._llm_client = OpenAI(api_key=api_key)
            except Exception:
                # If OpenAI client cannot be initialized, disable LLM fallback
                self.use_llm = False

    def _classify_by_rules(
        self, text: str, claim: Optional[Claim] = None
    ) -> Optional[tuple[str, float]]:
        """
        Classify using rule-based approach.

        Args:
            text: The claim text to classify
            claim: Optional Claim object with extracted information

        Returns:
            Tuple of (domain, confidence) or None if no rule matches
        """
        text_lower = text.lower()

        # Check for finance domain
        has_percentage = claim and len(claim.percentages) > 0 if claim else False
        has_finance_keyword = any(
            re.search(r"\b" + re.escape(keyword) + r"\b", text_lower)
            for keyword in FINANCE_KEYWORDS
        )

        if has_percentage or has_finance_keyword:
            confidence = 0.9 if has_percentage and has_finance_keyword else 0.8
            return ("finance", confidence)

        # Check for tech release domain
        has_tech_keyword = any(
            re.search(r"\b" + re.escape(keyword) + r"\b", text_lower)
            for keyword in TECH_RELEASE_KEYWORDS
        )

        if has_tech_keyword:
            return ("tech_release", 0.85)

        return None

    def _classify_by_llm(self, text: str) -> tuple[str, float]:
        """
        Classify using LLM fallback.

        Args:
            text: The claim text to classify

        Returns:
            Tuple of (domain, confidence)
        """
        self._init_llm_client()

        if not self._llm_client:
            # If LLM is not available, default to general domain
            return ("general", 0.5)

        try:
            prompt = f"""Classify this claim into one domain: finance, tech_release, or general.

Claim: "{text}"

Return the domain name (finance, tech_release, or general) and confidence (0-1).
Format: domain,confidence

Example: finance,0.85"""

            response = self._llm_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a domain classification expert."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=20,
                temperature=0.1,
            )

            result = response.choices[0].message.content.strip()

            # Parse the result
            parts = result.split(",")
            if len(parts) == 2:
                domain = parts[0].strip()
                confidence = float(parts[1].strip())

                # Validate domain
                if domain in ["finance", "tech_release", "general"]:
                    return (domain, min(max(confidence, 0.0), 1.0))

        except Exception:
            # If LLM fails, default to general domain
            pass

        return ("general", 0.5)

    def classify(self, text: str, claim: Optional[Claim] = None) -> DomainResult:
        """
        Classify claim into a domain using hybrid approach.

        First attempts rule-based classification, then falls back to LLM if needed.

        Args:
            text: The claim text to classify
            claim: Optional Claim object with extracted information

        Returns:
            DomainResult with domain and confidence
        """
        # Try rule-based classification first
        rule_result = self._classify_by_rules(text, claim)

        if rule_result:
            domain, confidence = rule_result
            return DomainResult(domain=domain, confidence=confidence)

        # Fall back to LLM if rules didn't match
        if self.use_llm:
            domain, confidence = self._classify_by_llm(text)
            return DomainResult(domain=domain, confidence=confidence)

        # Default to general domain if no LLM fallback
        return DomainResult(domain="general", confidence=0.5)


def classify_domain(text: str, claim: Optional[Claim] = None, use_llm: bool = True) -> DomainResult:
    """
    Classify a claim into a domain.

    Args:
        text: The claim text to classify
        claim: Optional Claim object with extracted information
        use_llm: Whether to use LLM fallback for unclear cases

    Returns:
        DomainResult with domain and confidence
    """
    classifier = DomainClassifier(use_llm=use_llm)
    return classifier.classify(text, claim)
