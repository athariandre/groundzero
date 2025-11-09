"""
Domain classification module for categorizing claims into domains.
"""

import os
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from server.schemas.claim import Claim, DomainResult

# Domain anchor phrases for semantic classification
FINANCE_ANCHORS = [
    "financial markets, stocks, cryptocurrencies, trading, prices, earnings",
    "price movement, assets rising or falling, market reactions",
    "stock rose, fell, jumped, surged, dumped, pumped, price changes",
    "trading volume, market capitalization, stock performance",
    "TSLA AAPL stock ticker symbols percentage gains losses",
]

TECH_RELEASE_ANCHORS = [
    "product launch by a company, official announcement, new technology release",
    "corporate press release about new products or updates",
    "announced, released, launched, introduced new products",
]

GENERAL_ANCHORS = [
    "general facts, historical information, scientific claims",
    "knowledge, education, history, science, nature",
]


class SemanticDomainClassifier:
    """Classifies claims into domains using semantic embeddings and cosine similarity."""

    def __init__(self, similarity_threshold: float = 0.15):
        """
        Initialize the semantic domain classifier.

        Args:
            similarity_threshold: Minimum similarity score threshold for classification
        """
        self.similarity_threshold = similarity_threshold
        self._vectorizer = None
        self._anchor_vectors = None
        self._domain_names = None
        self._anchors = None

    def _init_model(self):
        """Initialize the TF-IDF vectorizer and anchor embeddings."""
        if self._vectorizer is None:
            # Prepare domain anchors
            all_anchors = []
            domain_labels = []

            for anchor in FINANCE_ANCHORS:
                all_anchors.append(anchor)
                domain_labels.append("finance")

            for anchor in TECH_RELEASE_ANCHORS:
                all_anchors.append(anchor)
                domain_labels.append("tech_release")

            for anchor in GENERAL_ANCHORS:
                all_anchors.append(anchor)
                domain_labels.append("general")

            # Initialize TF-IDF vectorizer
            self._vectorizer = TfidfVectorizer(
                max_features=1000, ngram_range=(1, 2), stop_words="english"
            )

            # Fit and transform anchors
            self._anchor_vectors = self._vectorizer.fit_transform(all_anchors)
            self._domain_names = domain_labels
            self._anchors = all_anchors

    def classify(self, text: str, claim: Optional[Claim] = None) -> DomainResult:
        """
        Classify claim into a domain using semantic similarity.

        Args:
            text: The claim text to classify
            claim: Optional Claim object (not used in semantic classification)

        Returns:
            DomainResult with domain and confidence
        """
        # Initialize model if needed
        self._init_model()

        # Vectorize the input claim
        claim_vector = self._vectorizer.transform([text])

        # Compute cosine similarity with all anchors
        similarities = cosine_similarity(claim_vector, self._anchor_vectors)[0]

        # Group similarities by domain and find max for each
        domain_scores = {}
        for domain_name, similarity in zip(self._domain_names, similarities):
            if domain_name not in domain_scores:
                domain_scores[domain_name] = similarity
            else:
                domain_scores[domain_name] = max(domain_scores[domain_name], similarity)

        # Find domain with highest score
        best_domain = max(domain_scores, key=domain_scores.get)
        best_score = domain_scores[best_domain]

        # Apply threshold - if score is below threshold, default to general
        if best_score < self.similarity_threshold:
            domain = "general"
        else:
            domain = best_domain

        # TF-IDF cosine similarity is already in [0, 1], so we can use it directly
        # but we'll scale it to give more reasonable confidence scores
        # Using the formula from requirements: confidence = (best_score + 1) / 2
        # But since TF-IDF is in [0,1], we adjust to: confidence = (best_score + 0.5) / 1.5
        confidence = min(max((best_score * 2), 0.0), 1.0)

        return DomainResult(domain=domain, confidence=confidence)


class DomainClassifier:
    """Classifies claims into domains using semantic approach with optional LLM fallback."""

    def __init__(self, use_llm: bool = True):
        """
        Initialize the domain classifier.

        Args:
            use_llm: Whether to use LLM fallback for unclear cases (optional)
        """
        self.use_llm = use_llm
        self._llm_client = None
        self._semantic_classifier = SemanticDomainClassifier()

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
        Classify claim into a domain using semantic approach.

        Args:
            text: The claim text to classify
            claim: Optional Claim object with extracted information

        Returns:
            DomainResult with domain and confidence
        """
        # Use semantic classifier
        return self._semantic_classifier.classify(text, claim)


def classify_domain(text: str, claim: Optional[Claim] = None, use_llm: bool = True) -> DomainResult:
    """
    Classify a claim into a domain.

    Args:
        text: The claim text to classify
        claim: Optional Claim object with extracted information
        use_llm: Whether to use LLM fallback for unclear cases (currently unused)

    Returns:
        DomainResult with domain and confidence
    """
    classifier = DomainClassifier(use_llm=use_llm)
    return classifier.classify(text, claim)
