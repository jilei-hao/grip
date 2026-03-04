"""
GRIP — Core Pipeline
Orchestrates: fetch → deduplicate → score → post.
Separated from CLI so it can be imported and tested independently.
"""

from __future__ import annotations

from grip.config import Settings, load_settings
from grip.fetchers.arxiv import ArxivFetcher
from grip.fetchers.medrxiv_biorxiv import BioRxivFetcher
from grip.fetchers.pubmed import PubMedFetcher
from grip.notifier.slack import SlackNotifier
from grip.profile.manager import ProfileManager
from grip.scorer.claude_scorer import ClaudeScorer
from grip.utils.dedup import deduplicate


def run_digest(settings: Settings | None = None, dry_run: bool = False) -> list[dict]:
    """
    Full daily pipeline: fetch → deduplicate → score → post.

    Args:
        settings: override defaults (useful for testing)
        dry_run: if True, skip posting to Slack

    Returns:
        list of selected paper dicts (useful for testing / inspection)
    """
    s = settings or load_settings()

    # 1. Load interest profile
    profile = ProfileManager(s).load()

    # 2. Fetch from all active sources
    papers = []
    papers += ArxivFetcher(
        search_terms=s.search_terms,
        max_results=s.max_fetch_per_source,
        days_lookback=s.days_lookback,
    ).fetch_papers()

    papers += BioRxivFetcher(
        search_terms=s.search_terms,
        server="biorxiv",
        days_lookback=s.days_lookback,
        max_results=s.max_fetch_per_source,
    ).fetch_papers()

    papers += BioRxivFetcher(
        search_terms=s.search_terms,
        server="medrxiv",
        days_lookback=s.days_lookback,
        max_results=s.max_fetch_per_source,
    ).fetch_papers()

    papers += PubMedFetcher(
        search_terms=s.search_terms,
        days_lookback=s.days_lookback,
        max_results=s.max_fetch_per_source,
        api_key=s.ncbi_api_key,
    ).fetch_papers()

    # Add more sources here as you implement them:
    # from grip.fetchers.semantic_scholar import SemanticScholarFetcher
    # papers += SemanticScholarFetcher(s.search_terms).fetch_papers()
    #
    # from grip.fetchers.rss import RSSFetcher
    # papers += RSSFetcher(feed_urls=[...]).fetch_papers()

    # 3. Deduplicate across sources
    papers = deduplicate(papers)
    print(f"[pipeline] {len(papers)} unique papers after deduplication.")

    if not papers:
        print("[pipeline] No papers found. Try expanding search terms or days_lookback.")
        return []

    # 4. Score with Claude
    selected = ClaudeScorer(s).score(papers, profile)

    if not selected:
        print("[pipeline] No papers selected. Check interest profile or search terms.")
        return []

    # 5. Post to Slack
    if dry_run:
        print("\n[pipeline] DRY RUN — skipping Slack post. Would have sent:")
        for i, p in enumerate(selected, 1):
            print(f"  {i}. [{p.get('relevance_score', '?')}/10] {p['title']}")
    else:
        SlackNotifier(s).post_digest(selected)

    return selected


def run_profile_update(settings: Settings | None = None) -> bool:
    """Weekly profile update from accumulated feedback."""
    from grip.feedback.updater import ProfileUpdater
    return ProfileUpdater(settings or load_settings()).run_update()
