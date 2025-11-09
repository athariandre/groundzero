"""
Tests for the check_claim API endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)


class TestCheckClaimAPI:
    """Test cases for /check_claim endpoints."""

    def test_parse_claim_finance(self):
        """Test parsing a finance-related claim."""
        response = client.post("/check_claim/parse", json={"claim_text": "AAPL rose 10% today"})
        assert response.status_code == 200
        data = response.json()

        # Check claim extraction
        assert "claim" in data
        claim = data["claim"]
        assert claim["raw"] == "AAPL rose 10% today"
        assert "AAPL" in claim["tickers"]
        assert 10.0 in claim["percentages"]
        assert claim["date_hint"] == "today"
        assert claim["event_type"] == "price_movement"

        # Check domain classification
        assert "domain" in data
        domain = data["domain"]
        assert domain["domain"] == "finance"
        assert 0.0 <= domain["confidence"] <= 1.0

    def test_parse_claim_tech(self):
        """Test parsing a tech-related claim."""
        response = client.post(
            "/check_claim/parse",
            json={"claim_text": "Apple announced a new iPhone yesterday"},
        )
        assert response.status_code == 200
        data = response.json()

        # Check claim extraction
        assert "claim" in data
        claim = data["claim"]
        assert claim["raw"] == "Apple announced a new iPhone yesterday"
        assert "Apple" in claim["companies"]
        assert claim["date_hint"] == "yesterday"
        assert claim["event_type"] == "tech_release"

        # Check domain classification
        assert "domain" in data
        domain = data["domain"]
        assert domain["domain"] == "tech_release"

    def test_parse_claim_general(self):
        """Test parsing a general claim."""
        response = client.post(
            "/check_claim/parse", json={"claim_text": "This is just a statement"}
        )
        assert response.status_code == 200
        data = response.json()

        # Check claim extraction
        assert "claim" in data
        claim = data["claim"]
        assert claim["raw"] == "This is just a statement"
        assert len(claim["tickers"]) == 0
        assert len(claim["companies"]) == 0
        assert len(claim["percentages"]) == 0

        # Check domain classification
        assert "domain" in data
        domain = data["domain"]
        assert domain["domain"] == "general"

    def test_parse_claim_multiple_tickers(self):
        """Test parsing claim with multiple tickers."""
        response = client.post(
            "/check_claim/parse",
            json={"claim_text": "TSLA and NVDA both jumped 5% this morning"},
        )
        assert response.status_code == 200
        data = response.json()

        claim = data["claim"]
        assert "TSLA" in claim["tickers"]
        assert "NVDA" in claim["tickers"]
        assert 5.0 in claim["percentages"]
        assert claim["date_hint"] == "this morning"

    def test_parse_claim_missing_field(self):
        """Test that missing claim_text returns error."""
        response = client.post("/check_claim/parse", json={})
        assert response.status_code == 422  # Validation error

    def test_parse_claim_empty_text(self):
        """Test parsing empty claim text."""
        response = client.post("/check_claim/parse", json={"claim_text": ""})
        assert response.status_code == 200
        data = response.json()

        claim = data["claim"]
        assert claim["raw"] == ""
        assert len(claim["tickers"]) == 0
        assert len(claim["companies"]) == 0

    def test_response_structure(self):
        """Test that response has correct structure."""
        response = client.post("/check_claim/parse", json={"claim_text": "Test claim"})
        assert response.status_code == 200
        data = response.json()

        # Check top-level keys
        assert "claim" in data
        assert "domain" in data

        # Check claim structure
        claim = data["claim"]
        assert "raw" in claim
        assert "tickers" in claim
        assert "companies" in claim
        assert "percentages" in claim
        assert "date_hint" in claim
        assert "event_type" in claim

        # Check domain structure
        domain = data["domain"]
        assert "domain" in domain
        assert "confidence" in domain

    def test_parse_claim_complex(self):
        """Test parsing a complex claim with multiple features."""
        text = "Tesla and NVIDIA stock prices surged 15% and 20% today after both announced new releases"
        response = client.post("/check_claim/parse", json={"claim_text": text})
        assert response.status_code == 200
        data = response.json()

        claim = data["claim"]
        assert "Tesla" in claim["companies"] or "NVIDIA" in claim["companies"]
        assert len(claim["percentages"]) > 0
        assert claim["date_hint"] == "today"
        # Could be either finance or tech_release depending on which rules match first
        assert data["domain"]["domain"] in ["finance", "tech_release"]
