"""
Finance Oracle for GroundZero.

Validates claims about price movements by analyzing cached price data and news events.
Example: "SOL jumped 8% after ETF approval this morning."
"""

import json
from datetime import datetime, timedelta, timezone
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
        base_data_dir = Path(__file__).parent.parent.parent / "data"
        self.price_data_dir = base_data_dir / "prices"
        self.news_data_dir = base_data_dir / "news"

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

        # Extract event timestamp (with price data for snapping)
        event_timestamp = self._extract_event_timestamp(claim, news_data, price_data)

        if event_timestamp is None:
            # If we can't find an event, return uncertain
            return OracleResult(
                oracle_name=self.name,
                verdict="uncertain",
                confidence=0.3,
                evidence=self._build_evidence_items(news_data, ticker, "uncertain"),
                domain_context={
                    "reason": "Could not identify event timestamp",
                    "ticker": ticker,
                },
            )

        # Compute metrics
        metrics = self._compute_metrics(price_data, event_timestamp, claim.percentages)

        if metrics is None:
            return OracleResult(
                oracle_name=self.name,
                verdict="uncertain",
                confidence=0.3,
                evidence=self._build_evidence_items(news_data, ticker, "uncertain"),
                domain_context={
                    "reason": "Insufficient data around event time",
                    "ticker": ticker,
                    "event_timestamp": event_timestamp.isoformat() if event_timestamp else None,
                },
            )

        # Classify the claim
        verdict, confidence = self._classify_claim(metrics)

        # Build evidence items
        evidence = self._build_evidence_items(news_data, ticker, verdict)

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

        Supports two CSV schemas:
        1. Simple: timestamp, price, volume
        2. OHLC: timestamp, open, high, low, close, volume (price = close)

        Args:
            ticker: Stock ticker symbol

        Returns:
            DataFrame with price data or None if not found
        """
        csv_path = self.price_data_dir / f"{ticker}.csv"
        if not csv_path.exists():
            return None

        try:
            df = pd.read_csv(csv_path)

            # Check for simple schema (timestamp, price, volume)
            if {"timestamp", "price", "volume"}.issubset(df.columns):
                pass
            # Check for OHLC schema (timestamp, open, high, low, close, volume)
            elif {"timestamp", "open", "high", "low", "close", "volume"}.issubset(df.columns):
                df["price"] = df["close"]
            else:
                return None

            # Parse timestamps with UTC awareness and handle errors
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

            # Drop rows with invalid timestamps and sort by timestamp
            df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

            return df[["timestamp", "price", "volume"]]
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
        json_path = self.news_data_dir / f"{ticker}_news.json"
        if not json_path.exists():
            return None

        try:
            with open(json_path) as f:
                news = json.load(f)
            return news if isinstance(news, list) else None
        except Exception:
            return None

    def _extract_event_timestamp(
        self, claim: Claim, news_data: Optional[list], price_data: Optional[pd.DataFrame] = None
    ) -> Optional[datetime]:
        """
        Extract event timestamp from claim or news data and snap to nearest price bar.

        Args:
            claim: The claim object
            news_data: List of news items
            price_data: DataFrame with price data for timestamp snapping

        Returns:
            Event timestamp (UTC timezone-aware, snapped to nearest price bar) or None if not found
        """
        raw_timestamp = None

        # Try to use date_hint first
        if claim.date_hint:
            now = datetime.now(timezone.utc)
            if "today" in claim.date_hint.lower():
                # Market open 9:30 AM ET = 14:30 UTC (winter) / 13:30 UTC (summer DST)
                # Use 14:30 UTC as default (EST)
                raw_timestamp = now.replace(hour=14, minute=30, second=0, microsecond=0)
            elif "yesterday" in claim.date_hint.lower():
                # Use previous day at market open
                yesterday = now - timedelta(days=1)
                raw_timestamp = yesterday.replace(hour=14, minute=30, second=0, microsecond=0)
            elif "this morning" in claim.date_hint.lower():
                # Use current day at market open
                raw_timestamp = now.replace(hour=14, minute=30, second=0, microsecond=0)

        # Try to extract from news data with relevance scoring
        if raw_timestamp is None and news_data:
            ticker = claim.tickers[0] if claim.tickers else None
            companies = claim.companies if claim.companies else []

            best_score = -1
            best_timestamp = None

            for item in news_data:
                if "timestamp" not in item:
                    continue

                # Calculate relevance score
                score = 0
                title = item.get("title", "").lower()
                content = item.get(
                    "summary", item.get("content", item.get("description", ""))
                ).lower()

                # Check for ticker mention
                if ticker and ticker.lower() in title:
                    score += 3
                if ticker and ticker.lower() in content:
                    score += 1

                # Check for company mention
                for company in companies:
                    if company.lower() in title:
                        score += 2
                    if company.lower() in content:
                        score += 1

                if score > best_score:
                    best_score = score
                    try:
                        ts = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
                        # Ensure timezone-aware
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        best_timestamp = ts
                    except Exception:
                        continue

            if best_timestamp is not None:
                raw_timestamp = best_timestamp

        # Snap to nearest price bar if we have price data
        if raw_timestamp is not None and price_data is not None and len(price_data) > 0:
            return self._snap_to_nearest_bar(raw_timestamp, price_data)

        return raw_timestamp

    def _snap_to_nearest_bar(self, timestamp: datetime, price_data: pd.DataFrame) -> datetime:
        """
        Snap a timestamp to the nearest price bar in the dataset.

        Args:
            timestamp: The raw timestamp to snap
            price_data: DataFrame with price data

        Returns:
            Timestamp of the nearest price bar
        """
        # Find the nearest timestamp in price_data
        time_diffs = (price_data["timestamp"] - timestamp).abs()
        nearest_idx = time_diffs.idxmin()
        return price_data.loc[nearest_idx, "timestamp"]

    def _compute_metrics(
        self,
        price_data: pd.DataFrame,
        event_timestamp: datetime,
        claim_percentages: Optional[list] = None,
    ) -> Optional[dict]:
        """
        Compute pre/post event returns and volume metrics using nearest bars.

        Args:
            price_data: DataFrame with price and volume data
            event_timestamp: Timestamp of the event (already snapped to nearest bar)
            claim_percentages: Percentages mentioned in claim for comparison

        Returns:
            Dictionary with metrics or None if insufficient data
        """
        # Find the event bar (should already be snapped)
        event_idx = (price_data["timestamp"] - event_timestamp).abs().idxmin()
        event_time = price_data.loc[event_idx, "timestamp"]

        # Define time windows (30 minutes before and after)
        pre_start = event_time - timedelta(minutes=30)
        post_end = event_time + timedelta(minutes=30)

        # Get data for pre-event window (before event_time)
        pre_data = price_data[
            (price_data["timestamp"] >= pre_start) & (price_data["timestamp"] < event_time)
        ]

        # Get data for post-event window (at and after event_time)
        post_data = price_data[
            (price_data["timestamp"] >= event_time) & (price_data["timestamp"] <= post_end)
        ]

        # Need at least some data points
        if len(pre_data) < 1 or len(post_data) < 1:
            return None

        # Calculate returns using first and last bars in each window
        if len(pre_data) >= 2:
            pre_event_return = (
                (pre_data["price"].iloc[-1] - pre_data["price"].iloc[0]) / pre_data["price"].iloc[0]
            ) * 100
        else:
            pre_event_return = 0.0

        post_event_return = (
            (post_data["price"].iloc[-1] - post_data["price"].iloc[0]) / post_data["price"].iloc[0]
        ) * 100

        # Calculate abnormal volume z-score
        # Try 7 days of historical data, fallback to all available data
        historical_start = event_time - timedelta(days=7)
        historical_data = price_data[
            (price_data["timestamp"] >= historical_start) & (price_data["timestamp"] < event_time)
        ]

        # If less than 7 days available, use all data before event
        if len(historical_data) < 10:
            historical_data = price_data[price_data["timestamp"] < event_time]

        if len(historical_data) > 1:
            historical_mean = historical_data["volume"].mean()
            historical_std = historical_data["volume"].std()

            if historical_std > 0:
                post_volume_mean = post_data["volume"].mean()
                abnormal_volume_z = (post_volume_mean - historical_mean) / historical_std
            else:
                abnormal_volume_z = 0.0
        else:
            abnormal_volume_z = 0.0

        # Check if claim percentages disagree with computed returns
        percentage_mismatch = False
        if claim_percentages and len(claim_percentages) > 0:
            claimed_pct = abs(claim_percentages[0])
            actual_pct = abs(post_event_return)
            # If claimed percentage differs from actual by more than 3%, flag it
            if abs(claimed_pct - actual_pct) > 3.0:
                percentage_mismatch = True

        return {
            "pre_event_return": float(pre_event_return),
            "post_event_return": float(post_event_return),
            "abnormal_volume_z": float(abnormal_volume_z),
            "percentage_mismatch": percentage_mismatch,
        }

    def _classify_claim(self, metrics: dict) -> tuple[str, float]:
        """
        Classify the claim based on computed metrics using PR4 spec formula.

        Args:
            metrics: Dictionary with pre/post returns and volume metrics

        Returns:
            Tuple of (verdict, confidence)
        """
        pre_return = metrics["pre_event_return"]
        post_return = metrics["post_event_return"]
        volume_z = metrics["abnormal_volume_z"]
        percentage_mismatch = metrics.get("percentage_mismatch", False)

        # Classify based on the rules:
        # - likely_true: post_event_return > 0 AND post_event_return > pre_event_return
        # - likely_false: pre_event_return > post_event_return
        # - uncertain: otherwise

        if post_return > 0 and post_return > pre_return:
            # Claim is likely true
            # Use PR4 spec confidence formula:
            # base_conf = max(|post|, |post - pre|) / 100, clamped [0.1, 0.9]
            # But scale by 10 to get reasonable confidence values
            return_diff = abs(post_return - pre_return)
            base_confidence = max(abs(post_return), return_diff) / 10.0
            base_confidence = max(0.1, min(0.9, base_confidence))

            # Boost confidence if abnormal volume (z-score > 1)
            if volume_z > 1.0:
                base_confidence = min(base_confidence + 0.1, 0.95)

            # Reduce confidence if percentage mismatch
            if percentage_mismatch:
                base_confidence = max(0.3, base_confidence - 0.2)

            return "likely_true", base_confidence

        elif pre_return > post_return:
            # Claim is likely false
            return_diff = abs(pre_return - post_return)
            base_confidence = max(abs(pre_return), return_diff) / 10.0
            base_confidence = max(0.1, min(0.9, base_confidence))

            # Boost confidence if abnormal volume
            if volume_z > 1.0:
                base_confidence = min(base_confidence + 0.1, 0.95)

            return "likely_false", base_confidence

        else:
            # Uncertain
            return "uncertain", 0.4

    def _build_evidence_items(
        self, news_data: Optional[list], ticker: str, verdict: str
    ) -> list[EvidenceItem]:
        """
        Build evidence items from news data with stance inference.

        Args:
            news_data: List of news items
            ticker: Stock ticker symbol
            verdict: The verdict classification to infer stance

        Returns:
            List of EvidenceItem objects with stance fields
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
            # Use summary field first, fallback to content/description
            content = item.get("summary", item.get("content", item.get("description", "")))
            excerpt = content[:200] if content else None

            # Infer stance based on verdict and content
            stance = None
            stance_conf = None

            if verdict in ["likely_true", "likely_false"]:
                # Simple heuristic: if likely_true, news supports;
                # if likely_false, unrelated
                if verdict == "likely_true":
                    stance = "supports"
                    stance_conf = 0.6
                elif verdict == "likely_false":
                    stance = "unrelated"
                    stance_conf = 0.5
            else:
                stance = "unrelated"
                stance_conf = 0.3

            evidence_items.append(
                EvidenceItem(
                    source=source,
                    title=title,
                    url=url,
                    published_at=timestamp,
                    stance=stance,
                    stance_conf=stance_conf,
                    extract=excerpt,
                )
            )

        return evidence_items
