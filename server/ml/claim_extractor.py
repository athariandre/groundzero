"""
Claim extraction module for identifying and extracting structured information from text.
"""

import re
from typing import Optional

from server.schemas.claim import Claim

# Predefined list of companies to match
KNOWN_COMPANIES = ["NVIDIA", "Apple", "Meta", "Tesla", "Google", "OpenAI"]

# Event type keywords
PRICE_MOVEMENT_KEYWORDS = [
    "rise",
    "rose",
    "pumped",
    "plunged",
    "fell",
    "surged",
    "jumped",
    "dumped",
]
TECH_RELEASE_KEYWORDS = ["announced", "released", "launched", "introduced"]


class ClaimExtractor:
    """Extracts structured claim information from raw text."""

    @staticmethod
    def extract_tickers(text: str) -> list[str]:
        """
        Extract stock tickers from text.

        Matches uppercase sequences of 1-5 letters that are likely tickers.

        Args:
            text: The input text to extract tickers from

        Returns:
            List of extracted ticker symbols
        """
        # Match 1-5 uppercase letters that are standalone words
        # Use word boundaries to avoid matching parts of regular words
        pattern = r"\b[A-Z]{1,5}\b"
        matches = re.findall(pattern, text)

        # Filter out common words that aren't tickers (simple heuristic)
        # Keep only if they look like tickers (typically 2-5 chars)
        # This is a simple approach; a more sophisticated one would use a ticker database
        common_words = {"I", "A", "IT", "US", "UK", "AI", "ML", "API", "CEO", "CTO", "CFO"}
        tickers = [m for m in matches if m not in common_words and len(m) >= 2]

        # Remove duplicates while preserving order
        seen = set()
        unique_tickers = []
        for ticker in tickers:
            if ticker not in seen:
                seen.add(ticker)
                unique_tickers.append(ticker)

        return unique_tickers

    @staticmethod
    def extract_companies(text: str) -> list[str]:
        """
        Extract known company names from text.

        Args:
            text: The input text to extract companies from

        Returns:
            List of matched company names
        """
        found_companies = []
        for company in KNOWN_COMPANIES:
            # Case-insensitive search for company name
            if re.search(r"\b" + re.escape(company) + r"\b", text, re.IGNORECASE):
                found_companies.append(company)

        return found_companies

    @staticmethod
    def extract_percentages(text: str) -> list[float]:
        """
        Extract percentage values from text.

        Matches patterns like "10%", "+5%", "down 3%", "-2.5%"

        Args:
            text: The input text to extract percentages from

        Returns:
            List of percentage values as floats
        """
        # Pattern matches optional +/-, optional "up/down", number, optional decimal, %
        pattern = r"[+\-]?\s*(?:up\s+|down\s+)?(\d+(?:\.\d+)?)\s*%"
        matches = re.findall(pattern, text, re.IGNORECASE)

        percentages = []
        for match in matches:
            try:
                percentages.append(float(match))
            except ValueError:
                continue

        return percentages

    @staticmethod
    def extract_date_hint(text: str) -> Optional[str]:
        """
        Extract date hints from text.

        Detects tokens like "today", "yesterday", "this morning", "last week"

        Args:
            text: The input text to extract date hints from

        Returns:
            First matched date hint or None
        """
        date_patterns = [
            r"\btoday\b",
            r"\byesterday\b",
            r"\bthis morning\b",
            r"\bthis afternoon\b",
            r"\bthis evening\b",
            r"\blast week\b",
            r"\blast month\b",
            r"\blast year\b",
            r"\bthis week\b",
            r"\bthis month\b",
            r"\bthis year\b",
        ]

        text_lower = text.lower()
        for pattern in date_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(0)

        return None

    @staticmethod
    def determine_event_type(text: str) -> Optional[str]:
        """
        Determine the event type based on keywords in the text.

        Args:
            text: The input text to analyze

        Returns:
            Event type: "price_movement", "tech_release", or None
        """
        text_lower = text.lower()

        # Check for price movement keywords
        for keyword in PRICE_MOVEMENT_KEYWORDS:
            if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
                return "price_movement"

        # Check for tech release keywords
        for keyword in TECH_RELEASE_KEYWORDS:
            if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
                return "tech_release"

        return None


def extract_claim(raw_text: str) -> Claim:
    """
    Extract structured claim information from raw text.

    Args:
        raw_text: The raw text to extract claims from

    Returns:
        Claim object with extracted information
    """
    extractor = ClaimExtractor()

    return Claim(
        raw=raw_text,
        tickers=extractor.extract_tickers(raw_text),
        companies=extractor.extract_companies(raw_text),
        percentages=extractor.extract_percentages(raw_text),
        date_hint=extractor.extract_date_hint(raw_text),
        event_type=extractor.determine_event_type(raw_text),
    )
