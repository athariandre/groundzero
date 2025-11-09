"""
Finance Oracle for GroundZero.

Validates claims about price movements by analyzing cached price data and news events.
Example: "SOL jumped 8% after ETF approval this morning."
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from server.oracles.base import Oracle
from server.schemas.claim import Claim, DomainResult
from server.schemas.oracle_result import EvidenceItem, OracleResult


class FinanceOracle(Oracle):
    """Oracle that validates price movement claims using cached data."""

    name = "finance"

    def __init__(self):
        """Initialize the Finance Oracle."""
        # Path to cached data
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "prices"

    def analyze(self, claim: Claim, domain: DomainResult) -> OracleResult:
        """
        Analyze a financial claim about price movements.

        Args:
            claim: The parsed claim to analyze
            domain: The domain classification result

        Returns:
            OracleResult with verdict, confidence, and evidence
        """
        # Check if we have a ticker to analyze
        if not claim.tickers:
            return OracleResult(
                oracle_name=self.name,
                verdict="unsupported",
                confidence=0.0,
                evidence=[],
                domain_context={"reason": "No ticker identified in claim"},
            )

        # Use the first ticker if multiple are present
        ticker = claim.tickers[0]

        # Load cached data
        price_data = self._load_price_data(ticker)
        news_data = self._load_news_data(ticker)

        if price_data is None:
            return OracleResult(
                oracle_name=self.name,
                verdict="unsupported",
                confidence=0.0,
                evidence=[],
                domain_context={"reason": f"No cached price data for {ticker}"},
            )

        # Extract event timestamp
        event_timestamp = self._extract_event_timestamp(claim, news_data)

        if event_timestamp is None:
            # If we can't find an event, return uncertain
            return OracleResult(
                oracle_name=self.name,
                verdict="uncertain",
                confidence=0.3,
                evidence=self._build_evidence_items(news_data, ticker),
                domain_context={
                    "reason": "Could not identify event timestamp",
                    "ticker": ticker,
                },
            )

        # Compute metrics
        metrics = self._compute_metrics(price_data, event_timestamp)

        if metrics is None:
            return OracleResult(
                oracle_name=self.name,
                verdict="uncertain",
                confidence=0.3,
                evidence=self._build_evidence_items(news_data, ticker),
                domain_context={
                    "reason": "Insufficient data around event time",
                    "ticker": ticker,
                    "event_timestamp": event_timestamp.isoformat() if event_timestamp else None,
                },
            )

        # Classify the claim
        verdict, confidence = self._classify_claim(metrics)

        # Build evidence items
        evidence = self._build_evidence_items(news_data, ticker)

        return OracleResult(
            oracle_name=self.name,
            verdict=verdict,
            confidence=confidence,
            evidence=evidence,
            domain_context={
                "ticker": ticker,
                "event_timestamp": event_timestamp.isoformat() if event_timestamp else None,
                "pre_event_return": metrics.get("pre_event_return"),
                "post_event_return": metrics.get("post_event_return"),
                "abnormal_volume_z": metrics.get("abnormal_volume_z"),
            },
        )

    def _load_price_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Load cached price data for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            DataFrame with price data or None if not found
        """
        csv_path = self.data_dir / f"{ticker}.csv"
        if not csv_path.exists():
            return None

        try:
            df = pd.read_csv(csv_path)
            # Ensure we have required columns
            required_cols = ["timestamp", "price", "volume"]
            if not all(col in df.columns for col in required_cols):
                return None

            # Parse timestamps
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        except Exception:
            return None

    def _load_news_data(self, ticker: str) -> Optional[list]:
        """
        Load cached news/events data for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of news items or None if not found
        """
        json_path = self.data_dir / f"{ticker}_news.json"
        if not json_path.exists():
            return None

        try:
            with open(json_path) as f:
                news = json.load(f)
            return news if isinstance(news, list) else None
        except Exception:
            return None

    def _extract_event_timestamp(
        self, claim: Claim, news_data: Optional[list]
    ) -> Optional[datetime]:
        """
        Extract event timestamp from claim or news data.

        Args:
            claim: The claim object
            news_data: List of news items

        Returns:
            Event timestamp or None if not found
        """
        # Try to use date_hint first
        if claim.date_hint:
            now = datetime.now()
            if "today" in claim.date_hint.lower():
                # Use current date at market open (9:30 AM)
                return now.replace(hour=9, minute=30, second=0, microsecond=0)
            elif "yesterday" in claim.date_hint.lower():
                # Use previous day at market open
                yesterday = now - timedelta(days=1)
                return yesterday.replace(hour=9, minute=30, second=0, microsecond=0)
            elif "this morning" in claim.date_hint.lower():
                # Use current day at market open
                return now.replace(hour=9, minute=30, second=0, microsecond=0)

        # Try to extract from news data
        if news_data:
            for item in news_data:
                # Check if ticker or company is mentioned
                if "timestamp" in item:
                    try:
                        return datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
                    except Exception:
                        continue

        return None

    def _compute_metrics(
        self, price_data: pd.DataFrame, event_timestamp: datetime
    ) -> Optional[dict]:
        """
        Compute pre/post event returns and volume metrics.

        Args:
            price_data: DataFrame with price and volume data
            event_timestamp: Timestamp of the event

        Returns:
            Dictionary with metrics or None if insufficient data
        """
        # Define time windows (30 minutes before and after)
        pre_start = event_timestamp - timedelta(minutes=30)
        pre_end = event_timestamp
        post_start = event_timestamp
        post_end = event_timestamp + timedelta(minutes=30)

        # Filter data
        pre_data = price_data[
            (price_data["timestamp"] >= pre_start) & (price_data["timestamp"] < pre_end)
        ]
        post_data = price_data[
            (price_data["timestamp"] >= post_start) & (price_data["timestamp"] <= post_end)
        ]

        # Need at least some data points
        if len(pre_data) < 2 or len(post_data) < 2:
            return None

        # Calculate returns
        pre_event_return = (
            (pre_data["price"].iloc[-1] - pre_data["price"].iloc[0]) / pre_data["price"].iloc[0]
        ) * 100

        post_event_return = (
            (post_data["price"].iloc[-1] - post_data["price"].iloc[0]) / post_data["price"].iloc[0]
        ) * 100

        # Calculate abnormal volume z-score
        # Use historical data (e.g., 7 days before event) for baseline
        historical_start = event_timestamp - timedelta(days=7)
        historical_data = price_data[
            (price_data["timestamp"] >= historical_start)
            & (price_data["timestamp"] < event_timestamp)
        ]

        if len(historical_data) > 0:
            historical_mean = historical_data["volume"].mean()
            historical_std = historical_data["volume"].std()

            if historical_std > 0:
                post_volume_mean = post_data["volume"].mean()
                abnormal_volume_z = (post_volume_mean - historical_mean) / historical_std
            else:
                abnormal_volume_z = 0.0
        else:
            abnormal_volume_z = 0.0

        return {
            "pre_event_return": float(pre_event_return),
            "post_event_return": float(post_event_return),
            "abnormal_volume_z": float(abnormal_volume_z),
        }

    def _classify_claim(self, metrics: dict) -> tuple[str, float]:
        """
        Classify the claim based on computed metrics.

        Args:
            metrics: Dictionary with pre/post returns and volume metrics

        Returns:
            Tuple of (verdict, confidence)
        """
        pre_return = metrics["pre_event_return"]
        post_return = metrics["post_event_return"]
        volume_z = metrics["abnormal_volume_z"]

        # Classify based on the rules:
        # - likely_true: post_event_return > 0 AND post_event_return > pre_event_return
        # - likely_false: pre_event_return > post_event_return
        # - uncertain: otherwise

        if post_return > 0 and post_return > pre_return:
            # Claim is likely true
            # Confidence increases with:
            # 1. Magnitude of post_return
            # 2. Difference between post and pre returns
            # 3. Abnormal volume
            return_diff = post_return - pre_return
            base_confidence = min(0.7 + (return_diff / 100), 0.95)

            # Boost confidence if abnormal volume
            if volume_z > 2.0:
                base_confidence = min(base_confidence + 0.05, 0.98)

            return "likely_true", base_confidence

        elif pre_return > post_return:
            # Claim is likely false
            # Higher confidence if pre_return is significantly higher
            return_diff = pre_return - post_return
            base_confidence = min(0.6 + (return_diff / 100), 0.90)

            return "likely_false", base_confidence

        else:
            # Uncertain
            return "uncertain", 0.4

    def _build_evidence_items(self, news_data: Optional[list], ticker: str) -> list[EvidenceItem]:
        """
        Build evidence items from news data.

        Args:
            news_data: List of news items
            ticker: Stock ticker symbol

        Returns:
            List of EvidenceItem objects
        """
        if not news_data:
            return []

        evidence_items = []
        for item in news_data[:5]:  # Limit to first 5 items
            # Extract title and timestamp
            title = item.get("title", "News item")
            timestamp = item.get("timestamp")
            source = item.get("source", "Unknown")
            url = item.get("url")

            # Extract first 200 characters as excerpt
            content = item.get("content", item.get("description", ""))
            excerpt = content[:200] if content else None

            evidence_items.append(
                EvidenceItem(
                    source=source,
                    title=title,
                    url=url,
                    published_at=timestamp,
                    extract=excerpt,
                )
            )

        return evidence_items
