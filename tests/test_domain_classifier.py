"""
Tests for the domain classification module.
"""

import pytest

from server.ml.domain_classifier import DomainClassifier, classify_domain
from server.schemas.claim import Claim


class TestDomainClassifier:
    """Test cases for DomainClassifier class."""

    def test_classify_finance_with_percentage(self):
        """Test classification of finance domain with percentage."""
        classifier = DomainClassifier(use_llm=False)
        text = "Stock rose 10% today"
        claim = Claim(
            raw=text,
            tickers=["AAPL"],
            companies=[],
            percentages=[10.0],
            date_hint="today",
            event_type="price_movement",
        )
        result = classifier.classify(text, claim)
        assert result.domain == "finance"
        assert result.confidence >= 0.8

    def test_classify_finance_with_keyword(self):
        """Test classification of finance domain with keyword."""
        classifier = DomainClassifier(use_llm=False)
        text = "Stock price jumped significantly"
        result = classifier.classify(text)
        assert result.domain == "finance"
        assert result.confidence >= 0.8

    def test_classify_tech_release(self):
        """Test classification of tech release domain."""
        classifier = DomainClassifier(use_llm=False)
        text = "Apple announced a new product"
        result = classifier.classify(text)
        assert result.domain == "tech_release"
        assert result.confidence >= 0.8

    def test_classify_general_no_llm(self):
        """Test classification defaults to general when no rules match and LLM disabled."""
        classifier = DomainClassifier(use_llm=False)
        text = "This is a generic statement about technology"
        result = classifier.classify(text)
        assert result.domain == "general"
        assert result.confidence == 0.5

    def test_classify_finance_multiple_keywords(self):
        """Test classification with multiple finance keywords."""
        classifier = DomainClassifier(use_llm=False)
        text = "The stock surged and jumped today"
        result = classifier.classify(text)
        assert result.domain == "finance"

    def test_classify_tech_multiple_keywords(self):
        """Test classification with multiple tech keywords."""
        classifier = DomainClassifier(use_llm=False)
        text = "Company released and launched new software"
        result = classifier.classify(text)
        assert result.domain == "tech_release"

    def test_classify_function_finance(self):
        """Test the classify_domain function with finance text."""
        text = "TSLA dumped 15% yesterday"
        claim = Claim(
            raw=text,
            tickers=["TSLA"],
            companies=[],
            percentages=[15.0],
            date_hint="yesterday",
            event_type="price_movement",
        )
        result = classify_domain(text, claim, use_llm=False)
        assert result.domain == "finance"
        assert result.confidence >= 0.8

    def test_classify_function_tech(self):
        """Test the classify_domain function with tech text."""
        text = "Google introduced new AI features"
        result = classify_domain(text, use_llm=False)
        assert result.domain == "tech_release"
        assert result.confidence >= 0.8

    def test_classify_function_general(self):
        """Test the classify_domain function with general text."""
        text = "The weather is nice today"
        result = classify_domain(text, use_llm=False)
        assert result.domain == "general"

    def test_confidence_range(self):
        """Test that confidence values are within valid range."""
        classifier = DomainClassifier(use_llm=False)
        text = "Stock fell dramatically"
        result = classifier.classify(text)
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_with_claim_object(self):
        """Test classification using Claim object with extracted data."""
        classifier = DomainClassifier(use_llm=False)
        text = "Stock movement today"
        claim = Claim(
            raw=text,
            tickers=[],
            companies=[],
            percentages=[5.0],
            date_hint="today",
            event_type="price_movement",
        )
        result = classifier.classify(text, claim)
        assert result.domain == "finance"

    def test_case_insensitive_classification(self):
        """Test that classification is case-insensitive."""
        classifier = DomainClassifier(use_llm=False)
        text = "STOCK PRICE ROSE TODAY"
        result = classifier.classify(text)
        assert result.domain == "finance"
