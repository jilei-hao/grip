"""Tests for settings loading."""

import os
import pytest
from grip.config import load_settings


def test_default_settings():
    s = load_settings()
    assert s.days_lookback == 1
    assert s.top_n_papers == 5


def test_env_override(monkeypatch):
    monkeypatch.setenv("GRIP_TOP_N", "10")
    monkeypatch.setenv("GRIP_DAYS_LOOKBACK", "3")
    s = load_settings()
    assert s.top_n_papers == 10
    assert s.days_lookback == 3


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    s = load_settings()
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        _ = s.anthropic_api_key


def test_search_terms_from_env(monkeypatch):
    monkeypatch.setenv("GRIP_SEARCH_TERMS", "protein folding,cryo-EM,molecular dynamics")
    s = load_settings()
    assert "protein folding" in s.search_terms
    assert len(s.search_terms) == 3
