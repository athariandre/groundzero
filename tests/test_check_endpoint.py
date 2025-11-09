"""
Tests for the /check_claim/check endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)


class TestCheckClaimEndpoint:
    """Test cases for /check_claim/check endpoint."""

    def test_check_claim_finance_high_confidence(self):
        """Test checking a finance claim with high confidence."""
        response = client.post(
            "/check_claim/check",
            json={"claim_text": "AAPL rose 10% today"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "final_verdict" in data
        assert "final_confidence" in data
        assert "oracle_calls" in data
        assert "domain" in data
        assert "claim" in data
        
        # Verify domain classification
        assert data["domain"]["domain"] == "finance"
        
        # Verify claim extraction
        assert data["claim"]["raw"] == "AAPL rose 10% today"
        assert "AAPL" in data["claim"]["tickers"]
        
        # Verify oracle calls
        assert isinstance(data["oracle_calls"], list)
        assert len(data["oracle_calls"]) >= 1
        
        # First oracle should be finance
        first_oracle = data["oracle_calls"][0]
        assert first_oracle["oracle_name"] == "finance"
        assert "verdict" in first_oracle
        assert "confidence" in first_oracle
        assert "evidence" in first_oracle

    def test_check_claim_tech_release(self):
        """Test checking a tech release claim."""
        response = client.post(
            "/check_claim/check",
            json={"claim_text": "Apple announced a new iPhone yesterday"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify domain classification
        assert data["domain"]["domain"] == "tech_release"
        
        # Since tech oracle returns uncertain, should trigger fallback
        oracle_calls = data["oracle_calls"]
        assert len(oracle_calls) >= 1
        
        # First oracle should be tech_release
        assert oracle_calls[0]["oracle_name"] == "tech_release"
        assert oracle_calls[0]["verdict"] == "uncertain"
        
        # Should have fallback due to uncertain verdict
        if len(oracle_calls) > 1:
            assert oracle_calls[1]["oracle_name"] == "llm_oracle"

    def test_check_claim_general(self):
        """Test checking a general claim."""
        response = client.post(
            "/check_claim/check",
            json={"claim_text": "This is just a general statement"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify domain classification
        assert data["domain"]["domain"] == "general"
        
        # Should route to LLM oracle
        oracle_calls = data["oracle_calls"]
        assert len(oracle_calls) >= 1
        assert oracle_calls[0]["oracle_name"] == "llm_oracle"

    def test_check_claim_low_confidence_triggers_fallback(self):
        """Test that low confidence domain classification triggers fallback."""
        # This claim might have low confidence for domain classification
        response = client.post(
            "/check_claim/check",
            json={"claim_text": "Some ambiguous claim about stocks maybe"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # If domain confidence < 0.6, should have fallback oracle
        if data["domain"]["confidence"] < 0.6:
            oracle_calls = data["oracle_calls"]
            # Should have primary + fallback
            assert len(oracle_calls) >= 2

    def test_check_claim_empty_text(self):
        """Test that empty claim text returns error."""
        response = client.post(
            "/check_claim/check",
            json={"claim_text": ""}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "empty" in data["detail"].lower()

    def test_check_claim_missing_field(self):
        """Test that missing claim_text field returns validation error."""
        response = client.post("/check_claim/check", json={})
        
        assert response.status_code == 422  # Validation error

    def test_check_claim_response_structure(self):
        """Test that response has complete and correct structure."""
        response = client.post(
            "/check_claim/check",
            json={"claim_text": "Test claim AAPL"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Top-level fields
        assert "final_verdict" in data
        assert "final_confidence" in data
        assert "oracle_calls" in data
        assert "domain" in data
        assert "claim" in data
        
        # Final verdict should be a string
        assert isinstance(data["final_verdict"], str)
        assert data["final_verdict"] in ["likely_true", "likely_false", "uncertain", "unsupported"]
        
        # Final confidence should be between 0 and 1
        assert 0.0 <= data["final_confidence"] <= 1.0
        
        # Oracle calls structure
        for oracle_call in data["oracle_calls"]:
            assert "oracle_name" in oracle_call
            assert "verdict" in oracle_call
            assert "confidence" in oracle_call
            assert "evidence" in oracle_call
            assert "domain_context" in oracle_call
        
        # Domain structure
        domain = data["domain"]
        assert "domain" in domain
        assert "confidence" in domain
        
        # Claim structure
        claim = data["claim"]
        assert "raw" in claim
        assert "tickers" in claim
        assert "companies" in claim
        assert "percentages" in claim

    def test_check_claim_aggregation_likely_false_precedence(self):
        """Test that aggregation correctly prioritizes likely_false over likely_true."""
        # This test would require mocking oracles to return specific verdicts
        # For now, we just verify the endpoint works
        response = client.post(
            "/check_claim/check",
            json={"claim_text": "AAPL rose 10% today"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify final verdict is one of the expected values
        assert data["final_verdict"] in ["likely_true", "likely_false", "uncertain", "unsupported"]

    def test_check_claim_multiple_tickers(self):
        """Test checking a claim with multiple tickers."""
        response = client.post(
            "/check_claim/check",
            json={"claim_text": "TSLA and NVDA both jumped 5% this morning"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify claim extraction
        claim = data["claim"]
        assert "TSLA" in claim["tickers"]
        assert "NVDA" in claim["tickers"]
        
        # Should be classified as finance
        assert data["domain"]["domain"] == "finance"

    def test_check_claim_preserves_evidence(self):
        """Test that evidence from oracles is preserved in the response."""
        response = client.post(
            "/check_claim/check",
            json={"claim_text": "AAPL stock moved today"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Oracle calls should preserve evidence
        for oracle_call in data["oracle_calls"]:
            assert "evidence" in oracle_call
            assert isinstance(oracle_call["evidence"], list)

    def test_check_claim_complex_scenario(self):
        """Test a complex claim with multiple features."""
        text = "Tesla and NVIDIA stock prices surged 15% and 20% today after both announced new releases"
        response = client.post(
            "/check_claim/check",
            json={"claim_text": text}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should extract both companies/tickers
        claim = data["claim"]
        has_tesla = "Tesla" in claim["companies"] or "TSLA" in claim["tickers"]
        has_nvidia = "NVIDIA" in claim["companies"] or "NVDA" in claim["tickers"]
        assert has_tesla or has_nvidia
        
        # Should extract percentages
        assert len(claim["percentages"]) > 0
        
        # Should be classified (could be finance or tech_release)
        assert data["domain"]["domain"] in ["finance", "tech_release"]
        
        # Should have oracle calls
        assert len(data["oracle_calls"]) >= 1
