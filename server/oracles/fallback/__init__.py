"""
Fallback Oracle

Provides fallback mechanisms when primary oracles are unavailable.
"""

from server.oracles.fallback.oracle import LLMOracle

__all__ = ["LLMOracle"]
