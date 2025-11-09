"""
Tests for the domain classification module.
"""

from server.ml.domain_classifier import DomainClassifier, SemanticDomainClassifier, classify_domain
from server.schemas.claim import Claim


class TestSemanticDomainClassifier:
    """Test cases for SemanticDomainClassifier class."""

    def test_classify_finance_market_related(self):
        """Test classification of finance domain with market-related text."""
        classifier = SemanticDomainClassifier()
        text = "The stock market experienced significant price movements today"
        result = classifier.classify(text)
        assert result.domain == "finance"
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_finance_trading(self):
        """Test classification of finance domain with trading text."""
        classifier = SemanticDomainClassifier()
        text = "Bitcoin trading volume surged as prices rose"
        result = classifier.classify(text)
        assert result.domain == "finance"
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_tech_release_announcement(self):
        """Test classification of tech release domain with announcement."""
        classifier = SemanticDomainClassifier()
        text = "Company announces major product launch next month"
        result = classifier.classify(text)
        assert result.domain == "tech_release"
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_tech_release_press(self):
        """Test classification of tech release domain with press release."""
        classifier = SemanticDomainClassifier()
        text = "Tech giant releases new software update for users"
        result = classifier.classify(text)
        assert result.domain == "tech_release"
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_general_facts(self):
        """Test classification of general domain with factual information."""
        classifier = SemanticDomainClassifier()
        text = "The capital of France is Paris"
        result = classifier.classify(text)
        assert result.domain == "general"
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_general_scientific(self):
        """Test classification of general domain with scientific claim."""
        classifier = SemanticDomainClassifier()
        text = "Water molecules consist of hydrogen and oxygen atoms"
        result = classifier.classify(text)
        assert result.domain == "general"
        assert 0.0 <= result.confidence <= 1.0

    def test_threshold_fallback_to_general(self):
        """Test that low similarity scores fall back to general domain."""
        classifier = SemanticDomainClassifier(similarity_threshold=0.99)
        text = "Random unrelated text that should not match well"
        result = classifier.classify(text)
        assert result.domain == "general"

    def test_confidence_range(self):
        """Test that confidence values are within valid range."""
        classifier = SemanticDomainClassifier()
        text = "Stock prices fell today"
        result = classifier.classify(text)
        assert 0.0 <= result.confidence <= 1.0


class TestDomainClassifier:
    """Test cases for DomainClassifier class."""

    def test_classify_finance_with_percentage(self):
        """Test classification of finance domain with percentage."""
        classifier = DomainClassifier()
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
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_finance_with_keyword(self):
        """Test classification of finance domain with keyword."""
        classifier = DomainClassifier()
        text = "Stock price jumped significantly"
        result = classifier.classify(text)
        assert result.domain == "finance"
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_tech_release(self):
        """Test classification of tech release domain."""
        classifier = DomainClassifier()
        text = "Apple announced a new product"
        result = classifier.classify(text)
        assert result.domain == "tech_release"
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_general_no_llm(self):
        """Test classification defaults to general when semantic match is weak."""
        classifier = DomainClassifier()
        text = "The weather is nice today"
        result = classifier.classify(text)
        assert result.domain == "general"
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_finance_multiple_keywords(self):
        """Test classification with multiple finance keywords."""
        classifier = DomainClassifier()
        text = "The stock surged and jumped today"
        result = classifier.classify(text)
        assert result.domain == "finance"

    def test_classify_tech_multiple_keywords(self):
        """Test classification with multiple tech keywords."""
        classifier = DomainClassifier()
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
        result = classify_domain(text, claim)
        assert result.domain == "finance"
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_function_tech(self):
        """Test the classify_domain function with tech text."""
        text = "Google introduced new AI features"
        result = classify_domain(text)
        assert result.domain == "tech_release"
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_function_general(self):
        """Test the classify_domain function with general text."""
        text = "The weather is nice today"
        result = classify_domain(text)
        assert result.domain == "general"

    def test_confidence_range(self):
        """Test that confidence values are within valid range."""
        classifier = DomainClassifier()
        text = "Stock fell dramatically"
        result = classifier.classify(text)
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_with_claim_object(self):
        """Test classification using Claim object with extracted data."""
        classifier = DomainClassifier()
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
        classifier = DomainClassifier()
        text = "STOCK PRICE ROSE TODAY"
        result = classifier.classify(text)
        assert result.domain == "finance"
