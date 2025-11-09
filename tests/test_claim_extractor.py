"""
Tests for the claim extraction module.
"""


from server.ml.claim_extractor import ClaimExtractor, extract_claim


class TestClaimExtractor:
    """Test cases for ClaimExtractor class."""

    def test_extract_tickers_single(self):
        """Test extracting a single ticker."""
        text = "AAPL rose 5% today"
        tickers = ClaimExtractor.extract_tickers(text)
        assert "AAPL" in tickers

    def test_extract_tickers_multiple(self):
        """Test extracting multiple tickers."""
        text = "TSLA and NVDA both jumped this morning"
        tickers = ClaimExtractor.extract_tickers(text)
        assert "TSLA" in tickers
        assert "NVDA" in tickers

    def test_extract_tickers_no_duplicates(self):
        """Test that duplicate tickers are removed."""
        text = "AAPL rose, then AAPL fell"
        tickers = ClaimExtractor.extract_tickers(text)
        assert tickers.count("AAPL") == 1

    def test_extract_tickers_filters_common_words(self):
        """Test that common words are filtered out."""
        text = "I think AI is great"
        tickers = ClaimExtractor.extract_tickers(text)
        assert "I" not in tickers
        assert "AI" not in tickers

    def test_extract_companies_single(self):
        """Test extracting a single company."""
        text = "Apple announced new products"
        companies = ClaimExtractor.extract_companies(text)
        assert "Apple" in companies

    def test_extract_companies_multiple(self):
        """Test extracting multiple companies."""
        text = "Tesla and NVIDIA are competing"
        companies = ClaimExtractor.extract_companies(text)
        assert "Tesla" in companies
        assert "NVIDIA" in companies

    def test_extract_companies_case_insensitive(self):
        """Test that company extraction is case-insensitive."""
        text = "apple released a new iphone"
        companies = ClaimExtractor.extract_companies(text)
        assert "Apple" in companies

    def test_extract_percentages_simple(self):
        """Test extracting simple percentage."""
        text = "Stock rose 10%"
        percentages = ClaimExtractor.extract_percentages(text)
        assert 10.0 in percentages

    def test_extract_percentages_with_sign(self):
        """Test extracting percentage with + or - sign."""
        text = "Up +5% and down -3%"
        percentages = ClaimExtractor.extract_percentages(text)
        assert 5.0 in percentages
        assert 3.0 in percentages

    def test_extract_percentages_with_decimal(self):
        """Test extracting percentage with decimal."""
        text = "Increased by 2.5%"
        percentages = ClaimExtractor.extract_percentages(text)
        assert 2.5 in percentages

    def test_extract_percentages_with_words(self):
        """Test extracting percentage with up/down words."""
        text = "Down 15% today"
        percentages = ClaimExtractor.extract_percentages(text)
        assert 15.0 in percentages

    def test_extract_date_hint_today(self):
        """Test extracting 'today' date hint."""
        text = "Stock rose today"
        date_hint = ClaimExtractor.extract_date_hint(text)
        assert date_hint == "today"

    def test_extract_date_hint_yesterday(self):
        """Test extracting 'yesterday' date hint."""
        text = "Stock fell yesterday"
        date_hint = ClaimExtractor.extract_date_hint(text)
        assert date_hint == "yesterday"

    def test_extract_date_hint_compound(self):
        """Test extracting compound date hints."""
        text = "Stock surged this morning"
        date_hint = ClaimExtractor.extract_date_hint(text)
        assert date_hint == "this morning"

    def test_extract_date_hint_none(self):
        """Test when no date hint is present."""
        text = "Stock is trading"
        date_hint = ClaimExtractor.extract_date_hint(text)
        assert date_hint is None

    def test_determine_event_type_price_movement(self):
        """Test determining price movement event type."""
        text = "Stock rose 10%"
        event_type = ClaimExtractor.determine_event_type(text)
        assert event_type == "price_movement"

    def test_determine_event_type_tech_release(self):
        """Test determining tech release event type."""
        text = "Apple announced new iPhone"
        event_type = ClaimExtractor.determine_event_type(text)
        assert event_type == "tech_release"

    def test_determine_event_type_none(self):
        """Test when no event type can be determined."""
        text = "This is just a statement"
        event_type = ClaimExtractor.determine_event_type(text)
        assert event_type is None

    def test_extract_claim_full_finance(self):
        """Test full claim extraction for finance claim."""
        text = "AAPL rose 5% today"
        claim = extract_claim(text)
        assert claim.raw == text
        assert "AAPL" in claim.tickers
        assert 5.0 in claim.percentages
        assert claim.date_hint == "today"
        assert claim.event_type == "price_movement"

    def test_extract_claim_full_tech(self):
        """Test full claim extraction for tech claim."""
        text = "Apple announced a new product yesterday"
        claim = extract_claim(text)
        assert claim.raw == text
        assert "Apple" in claim.companies
        assert claim.date_hint == "yesterday"
        assert claim.event_type == "tech_release"

    def test_extract_claim_minimal(self):
        """Test claim extraction with minimal information."""
        text = "Just a simple statement"
        claim = extract_claim(text)
        assert claim.raw == text
        assert len(claim.tickers) == 0
        assert len(claim.companies) == 0
        assert len(claim.percentages) == 0
        assert claim.date_hint is None
        assert claim.event_type is None
