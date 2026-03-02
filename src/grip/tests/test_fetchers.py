"""Tests for fetcher contract and deduplication."""

import pytest
from grip.fetchers.base import Paper
from grip.utils.dedup import deduplicate


def make_paper(**kwargs) -> Paper:
    defaults = dict(
        title="Test Paper",
        authors=["Alice", "Bob"],
        abstract="An abstract.",
        url="https://arxiv.org/abs/1234.5678",
        published="2025-01-01",
        categories=["cs.LG"],
        source="arxiv",
        doi=None,
    )
    return Paper(**{**defaults, **kwargs})


def test_dedup_key_prefers_doi():
    p = make_paper(doi="10.1234/test")
    assert p.dedup_key() == "10.1234/test"


def test_dedup_key_falls_back_to_title():
    p = make_paper(doi=None, title="My Great Paper")
    assert p.dedup_key() == "my great paper"


def test_deduplicate_removes_exact_title_duplicates():
    papers = [
        make_paper(title="Same Title", source="arxiv"),
        make_paper(title="Same Title", source="semantic_scholar"),
        make_paper(title="Different Title", source="arxiv"),
    ]
    result = deduplicate(papers)
    assert len(result) == 2


def test_deduplicate_prefers_doi_copy():
    papers = [
        make_paper(title="Same Title", source="arxiv", doi=None),
        make_paper(title="Same Title", source="semantic_scholar", doi="10.1234/x"),
    ]
    result = deduplicate(papers)
    assert len(result) == 1
    assert result[0].doi == "10.1234/x"


def test_paper_to_prompt_str_includes_key_fields():
    p = make_paper(title="GRIP Paper", url="https://example.com")
    s = p.to_prompt_str()
    assert "GRIP Paper" in s
    assert "https://example.com" in s
    assert "An abstract." in s
