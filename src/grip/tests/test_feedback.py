"""Tests for feedback collection and logging."""

import json
import pytest
from pathlib import Path
from grip.config import Settings
from grip.feedback.collector import FeedbackCollector


@pytest.fixture
def tmp_settings(tmp_path):
    s = Settings()
    s.data_dir = tmp_path
    return s


def test_handle_thumbs_up_reaction(tmp_settings):
    collector = FeedbackCollector(tmp_settings)
    event = {
        "type": "reaction_added",
        "reaction": "thumbsup",
        "item": {"ts": "123456.789"},
        "user": "U123",
    }
    collector.handle_reaction(event)
    entries = collector.load_recent(days=1)
    assert len(entries) == 1
    assert entries[0]["sentiment"] == "positive"


def test_ignores_irrelevant_reactions(tmp_settings):
    collector = FeedbackCollector(tmp_settings)
    collector.handle_reaction({"type": "reaction_added", "reaction": "rocket"})
    entries = collector.load_recent(days=1)
    assert len(entries) == 0
