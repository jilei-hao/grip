"""
GRIP — Deduplication utility.
Used after aggregating papers from multiple sources.

Dedup strategy:
- Primary key: normalized title (catches same paper from different sources)
- Secondary: if both copies have DOIs and they match, also deduplicate
- When duplicate found, keep the copy with richer metadata (prefers DOI)
"""

from __future__ import annotations

from grip.fetchers.base import Paper


def deduplicate(papers: list[Paper]) -> list[Paper]:
    """
    Remove duplicate papers across sources.

    Uses normalized title as the canonical key (so the same paper appearing
    on both arXiv and Semantic Scholar gets deduplicated even if one has a
    DOI and the other doesn't). When a duplicate is found, the copy with
    a DOI wins (richer metadata).
    """
    seen: dict[str, Paper] = {}

    for paper in papers:
        # Always key by normalized title so cross-source duplicates merge
        key = paper.title.lower().strip()

        if key not in seen:
            seen[key] = paper
        elif paper.doi and not seen[key].doi:
            # Upgrade: this copy has a DOI, the stored one doesn't
            seen[key] = paper

    # Second pass: also deduplicate by DOI (catches title variations)
    doi_seen: dict[str, Paper] = {}
    result: list[Paper] = []
    for paper in seen.values():
        if paper.doi:
            doi_key = paper.doi.lower().strip()
            if doi_key in doi_seen:
                continue  # true duplicate via DOI
            doi_seen[doi_key] = paper
        result.append(paper)

    removed = len(papers) - len(result)
    if removed:
        print(f"[dedup] Removed {removed} duplicate(s).")
    return result
