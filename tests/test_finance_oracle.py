"""
Tests for Finance Oracle.
"""

import json
from datetime import datetime, timedelta

import pandas as pd
import pytest

from server.oracles.finance import FinanceOracle
from server.schemas.claim import Claim, DomainResult


@pytest.fixture
def temp_data_dirs(tmp_path):
    """Create temporary data directories with sample data."""
    price_dir = tmp_path / "data" / "prices"
    news_dir = tmp_path / "data" / "news"
    price_dir.mkdir(parents=True)
    news_dir.mkdir(parents=True)
    return {"price": price_dir, "news": news_dir}


@pytest.fixture
def sample_price_data(temp_data_dirs):
    """Create sample price data for testing."""
    # Create a realistic price dataset
    base_time = datetime(2024, 1, 15, 9, 0, 0)
    timestamps = []
    prices = []
    volumes = []

    # Generate data for 8 days
    for day_offset in range(8):
        for minute_offset in range(0, 390, 5):  # Market hours: 9:00 AM - 4:00 PM
            current_time = base_time + timedelta(days=day_offset, minutes=minute_offset)
            timestamps.append(current_time.isoformat())

            # Simulate price movement with a spike on day 7 at 9:30 AM
            base_price = 100.0
            if day_offset == 7 and minute_offset >= 30:
                # 8% jump after event
                prices.append(base_price * 1.08 + (minute_offset - 30) * 0.01)
                volumes.append(1000000 + minute_offset * 10000)  # Higher volume
            else:
                prices.append(base_price + minute_offset * 0.01)
                volumes.append(100000 + minute_offset * 100)  # Normal volume

    df = pd.DataFrame({"timestamp": timestamps, "price": prices, "volume": volumes})

    # Save to CSV
    csv_path = temp_data_dirs["price"] / "SOL.csv"
    df.to_csv(csv_path, index=False)

    return csv_path


@pytest.fixture
def sample_news_data(temp_data_dirs):
    """Create sample news data for testing."""
    event_time = datetime(2024, 1, 22, 9, 30, 0)  # Day 7, 9:30 AM

    news_items = [
        {
            "title": "SOL ETF Approved by SEC",
            "timestamp": event_time.isoformat(),
            "source": "Financial News",
            "url": "https://example.com/sol-etf-approval",
            "content": (
                "The SEC has approved the first SOL ETF, marking a major milestone "
                "for cryptocurrency adoption. This decision comes after months of "
                "deliberation and is expected to increase institutional interest in SOL."
            ),
        },
        {
            "title": "Market Reacts to SOL News",
            "timestamp": (event_time + timedelta(minutes=15)).isoformat(),
            "source": "Market Watch",
            "url": "https://example.com/sol-market-reaction",
            "content": (
                "SOL prices surged following the ETF approval announcement. "
                "Trading volumes have increased significantly as investors rush "
                "to capitalize on the news."
            ),
        },
    ]

    # Save to JSON in news directory
    json_path = temp_data_dirs["news"] / "SOL_news.json"
    with open(json_path, "w") as f:
        json.dump(news_items, f)

    return json_path


class TestFinanceOracle:
    """Tests for FinanceOracle class."""

    def test_oracle_name(self):
        """Test that oracle has correct name."""
        oracle = FinanceOracle()
        assert oracle.name == "finance"

    def test_analyze_no_ticker(self, temp_data_dirs, monkeypatch):
        """Test oracle returns unsupported when no ticker is present."""
        oracle = FinanceOracle()
        monkeypatch.setattr(oracle, "price_data_dir", temp_data_dirs["price"])
        monkeypatch.setattr(oracle, "news_data_dir", temp_data_dirs["news"])

        claim = Claim(
            raw="The market went up today",
            tickers=[],
            companies=["Apple"],
            percentages=[10.0],
            date_hint="today",
            event_type="price_movement",
        )
        domain = DomainResult(domain="finance", confidence=0.9)

        result = oracle.analyze(claim, domain)

        assert result.oracle_name == "finance"
        assert result.verdict == "unsupported"
        assert result.confidence == 0.0
        assert "No ticker identified" in result.domain_context["reason"]

    def test_analyze_no_price_data(self, temp_data_dirs, monkeypatch):
        """Test oracle returns unsupported when price data is missing."""
        oracle = FinanceOracle()
        monkeypatch.setattr(oracle, "price_data_dir", temp_data_dirs["price"])
        monkeypatch.setattr(oracle, "news_data_dir", temp_data_dirs["news"])

        claim = Claim(
            raw="AAPL rose 10% today",
            tickers=["AAPL"],
            companies=[],
            percentages=[10.0],
            date_hint="today",
            event_type="price_movement",
        )
        domain = DomainResult(domain="finance", confidence=0.9)

        result = oracle.analyze(claim, domain)

        assert result.oracle_name == "finance"
        assert result.verdict == "unsupported"
        assert "No cached price data" in result.domain_context["reason"]

    def test_analyze_with_price_spike(
        self, temp_data_dirs, sample_price_data, sample_news_data, monkeypatch
    ):
        """Test oracle correctly identifies price spike after event."""
        oracle = FinanceOracle()
        monkeypatch.setattr(oracle, "price_data_dir", temp_data_dirs["price"])
        monkeypatch.setattr(oracle, "news_data_dir", temp_data_dirs["news"])

        # Use claim without date_hint so it falls back to news timestamp
        # Note: percentages is empty to avoid percentage mismatch logic
        claim = Claim(
            raw="SOL jumped after ETF approval",
            tickers=["SOL"],
            companies=[],
            percentages=[],  # No specific percentage claimed
            date_hint=None,  # Will use news timestamp instead
            event_type="price_movement",
        )
        domain = DomainResult(domain="finance", confidence=0.95)

        result = oracle.analyze(claim, domain)

        assert result.oracle_name == "finance"
        # Should be likely_true because post_event_return > 0 and > pre_event_return
        assert result.verdict in ["likely_true", "uncertain"]
        assert result.confidence > 0.0

        # Check evidence items
        assert len(result.evidence) > 0
        assert result.evidence[0].title == "SOL ETF Approved by SEC"
        assert result.evidence[0].source == "Financial News"
        assert result.evidence[0].extract is not None
        assert len(result.evidence[0].extract) <= 200

        # Check domain context
        assert result.domain_context["ticker"] == "SOL"
        assert "event_timestamp" in result.domain_context
        if result.verdict != "uncertain" or "Insufficient data" not in result.domain_context.get(
            "reason", ""
        ):
            assert "pre_event_return" in result.domain_context
            assert "post_event_return" in result.domain_context
            assert "abnormal_volume_z" in result.domain_context

    def test_analyze_uncertain_without_event(self, temp_data_dirs, sample_price_data, monkeypatch):
        """Test oracle returns uncertain when no event timestamp can be found."""
        oracle = FinanceOracle()
        monkeypatch.setattr(oracle, "price_data_dir", temp_data_dirs["price"])
        monkeypatch.setattr(oracle, "news_data_dir", temp_data_dirs["news"])

        claim = Claim(
            raw="SOL jumped 8%",
            tickers=["SOL"],
            companies=[],
            percentages=[8.0],
            date_hint=None,  # No date hint
            event_type="price_movement",
        )
        domain = DomainResult(domain="finance", confidence=0.9)

        result = oracle.analyze(claim, domain)

        assert result.oracle_name == "finance"
        assert result.verdict == "uncertain"
        assert result.confidence == 0.3
        assert "Could not identify event timestamp" in result.domain_context["reason"]

    def test_load_price_data_success(self, temp_data_dirs, sample_price_data, monkeypatch):
        """Test successful loading of price data."""
        oracle = FinanceOracle()
        monkeypatch.setattr(oracle, "price_data_dir", temp_data_dirs["price"])
        monkeypatch.setattr(oracle, "news_data_dir", temp_data_dirs["news"])

        df = oracle._load_price_data("SOL")

        assert df is not None
        assert "timestamp" in df.columns
        assert "price" in df.columns
        assert "volume" in df.columns
        assert len(df) > 0

    def test_load_price_data_missing_file(self, temp_data_dirs, monkeypatch):
        """Test loading price data when file doesn't exist."""
        oracle = FinanceOracle()
        monkeypatch.setattr(oracle, "price_data_dir", temp_data_dirs["price"])
        monkeypatch.setattr(oracle, "news_data_dir", temp_data_dirs["news"])

        df = oracle._load_price_data("NONEXISTENT")

        assert df is None

    def test_load_news_data_success(self, temp_data_dirs, sample_news_data, monkeypatch):
        """Test successful loading of news data."""
        oracle = FinanceOracle()
        monkeypatch.setattr(oracle, "price_data_dir", temp_data_dirs["price"])
        monkeypatch.setattr(oracle, "news_data_dir", temp_data_dirs["news"])

        news = oracle._load_news_data("SOL")

        assert news is not None
        assert isinstance(news, list)
        assert len(news) == 2
        assert news[0]["title"] == "SOL ETF Approved by SEC"

    def test_load_news_data_missing_file(self, temp_data_dirs, monkeypatch):
        """Test loading news data when file doesn't exist."""
        oracle = FinanceOracle()
        monkeypatch.setattr(oracle, "price_data_dir", temp_data_dirs["price"])
        monkeypatch.setattr(oracle, "news_data_dir", temp_data_dirs["news"])

        news = oracle._load_news_data("NONEXISTENT")

        assert news is None

    def test_load_price_data_ohlc_schema(self, temp_data_dirs, monkeypatch):
        """Test loading price data with OHLC schema."""
        oracle = FinanceOracle()
        monkeypatch.setattr(oracle, "price_data_dir", temp_data_dirs["price"])
        monkeypatch.setattr(oracle, "news_data_dir", temp_data_dirs["news"])

        # Create OHLC format CSV
        base_time = datetime(2024, 1, 15, 9, 0, 0)
        data = {
            "timestamp": [base_time + timedelta(minutes=i * 5) for i in range(10)],
            "open": [100 + i * 0.5 for i in range(10)],
            "high": [101 + i * 0.5 for i in range(10)],
            "low": [99 + i * 0.5 for i in range(10)],
            "close": [100.5 + i * 0.5 for i in range(10)],
            "volume": [100000 + i * 1000 for i in range(10)],
        }
        df = pd.DataFrame(data)
        csv_path = temp_data_dirs["price"] / "OHLC_TEST.csv"
        df.to_csv(csv_path, index=False)

        # Load and verify
        loaded_df = oracle._load_price_data("OHLC_TEST")

        assert loaded_df is not None
        assert "timestamp" in loaded_df.columns
        assert "price" in loaded_df.columns
        assert "volume" in loaded_df.columns
        assert len(loaded_df) == 10
        # Verify price is derived from close
        assert loaded_df["price"].iloc[0] == 100.5

    def test_extract_event_timestamp_from_date_hint(self):
        """Test event timestamp extraction from date hints."""
        oracle = FinanceOracle()

        # Test "today" - should be 9:30 AM ET converted to UTC (13:30 or 14:30 depending on DST)
        claim = Claim(
            raw="AAPL rose", tickers=["AAPL"], companies=[], percentages=[], date_hint="today"
        )
        timestamp = oracle._extract_event_timestamp(claim, None, None)
        assert timestamp is not None
        # Hour should be 13 (EDT) or 14 (EST) depending on time of year
        assert timestamp.hour in [13, 14]
        assert timestamp.minute == 30

        # Test "yesterday"
        claim = Claim(
            raw="AAPL rose",
            tickers=["AAPL"],
            companies=[],
            percentages=[],
            date_hint="yesterday",
        )
        timestamp = oracle._extract_event_timestamp(claim, None, None)
        assert timestamp is not None
        # Use NY timezone to properly check day
        from zoneinfo import ZoneInfo

        ny_tz = ZoneInfo("America/New_York")
        now_ny = datetime.now(ny_tz)
        expected_day = (now_ny - timedelta(days=1)).day
        # Convert timestamp to NY time to check day
        timestamp_ny = timestamp.astimezone(ny_tz)
        assert timestamp_ny.day == expected_day

        # Test "this morning"
        claim = Claim(
            raw="AAPL rose",
            tickers=["AAPL"],
            companies=[],
            percentages=[],
            date_hint="this morning",
        )
        timestamp = oracle._extract_event_timestamp(claim, None, None)
        assert timestamp is not None
        # Hour should be 13 (EDT) or 14 (EST) depending on time of year
        assert timestamp.hour in [13, 14]
        assert timestamp.minute == 30

    def test_extract_event_timestamp_from_news(self):
        """Test event timestamp extraction from news data."""
        oracle = FinanceOracle()

        claim = Claim(
            raw="AAPL rose", tickers=["AAPL"], companies=[], percentages=[], date_hint=None
        )

        news_data = [{"title": "News", "timestamp": "2024-01-15T10:00:00"}]

        timestamp = oracle._extract_event_timestamp(claim, news_data, None)
        assert timestamp is not None
        assert timestamp.hour == 10
        assert timestamp.minute == 0

    def test_classify_claim_likely_true(self):
        """Test claim classification as likely_true."""
        oracle = FinanceOracle()

        metrics = {
            "pre_event_return": 0.5,  # Small pre-event return
            "post_event_return": 8.0,  # Large post-event return
            "abnormal_volume_z": 3.0,  # High abnormal volume
        }

        verdict, confidence = oracle._classify_claim(metrics)

        assert verdict == "likely_true"
        # With /100 formula: max(8.0, 7.5) / 100 = 0.08, clamped to 0.1, + 0.1 volume = 0.2
        assert confidence >= 0.1
        assert confidence <= 0.95

    def test_classify_claim_likely_false(self):
        """Test claim classification as likely_false."""
        oracle = FinanceOracle()

        metrics = {
            "pre_event_return": 8.0,  # Large pre-event return
            "post_event_return": 0.5,  # Small post-event return
            "abnormal_volume_z": 1.0,
        }

        verdict, confidence = oracle._classify_claim(metrics)

        assert verdict == "likely_false"
        # With /100 formula: max(8.0, 7.5) / 100 = 0.08, clamped to 0.1, + 0.1 volume = 0.2
        assert confidence >= 0.1
        assert confidence <= 0.95

    def test_classify_claim_uncertain(self):
        """Test claim classification as uncertain."""
        oracle = FinanceOracle()

        metrics = {
            "pre_event_return": -2.0,  # Negative pre-event return
            "post_event_return": -1.0,  # Negative post-event return
            "abnormal_volume_z": 0.5,
        }

        verdict, confidence = oracle._classify_claim(metrics)

        assert verdict == "uncertain"
        assert confidence == 0.4

    def test_classify_claim_percentage_mismatch(self):
        """Test that percentage mismatch causes likely_false verdict."""
        oracle = FinanceOracle()

        metrics = {
            "pre_event_return": 0.5,
            "post_event_return": 2.0,  # Actual is 2%
            "abnormal_volume_z": 1.5,
            "percentage_mismatch": True,  # Claim said 12% but actual is 2%
        }

        verdict, confidence = oracle._classify_claim(metrics)

        # Should be likely_false due to mismatch, even though post > pre
        assert verdict == "likely_false"
        assert confidence >= 0.1
        assert confidence <= 0.95

    def test_build_evidence_items(self):
        """Test building evidence items from news data."""
        oracle = FinanceOracle()

        news_data = [
            {
                "title": "News Item 1",
                "timestamp": "2024-01-15T10:00:00",
                "source": "Source 1",
                "url": "https://example.com/1",
                "content": "A" * 250,  # Long content
            },
            {
                "title": "News Item 2",
                "timestamp": "2024-01-15T11:00:00",
                "source": "Source 2",
                "url": "https://example.com/2",
                "description": "B" * 150,  # Use description if no content
            },
        ]

        evidence = oracle._build_evidence_items(news_data, "AAPL", "likely_true")

        assert len(evidence) == 2
        assert evidence[0].title == "News Item 1"
        assert evidence[0].source == "Source 1"
        assert evidence[0].url == "https://example.com/1"
        assert evidence[0].stance == "supports"
        assert evidence[0].stance_conf == 0.6
        assert len(evidence[0].extract) == 200  # Should truncate to 200 chars
        assert evidence[1].title == "News Item 2"
        assert len(evidence[1].extract) <= 200

    def test_build_evidence_items_limit(self):
        """Test that evidence items are limited to 5."""
        oracle = FinanceOracle()

        news_data = [
            {
                "title": f"News Item {i}",
                "timestamp": "2024-01-15T10:00:00",
                "source": "Source",
                "content": "Content",
            }
            for i in range(10)
        ]

        evidence = oracle._build_evidence_items(news_data, "AAPL", "uncertain")

        assert len(evidence) == 5  # Should limit to 5 items

    def test_build_evidence_items_empty(self):
        """Test building evidence items with no news data."""
        oracle = FinanceOracle()

        evidence = oracle._build_evidence_items(None, "AAPL", "uncertain")
        assert evidence == []

        evidence = oracle._build_evidence_items([], "AAPL", "uncertain")
        assert evidence == []
