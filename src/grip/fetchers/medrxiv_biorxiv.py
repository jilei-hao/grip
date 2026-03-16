"""
GRIP — bioRxiv / medRxiv Fetcher
Uses the public bioRxiv/medRxiv content API (no API key required).

The API returns all new preprints in a date range; client-side keyword
and optional category filtering is applied against title + abstract.

API docs: https://api.biorxiv.org/
"""

import json
import time
import urllib.request
from datetime import datetime, timedelta

from grip.config import get_ssl_context
from grip.fetchers.base import BaseFetcher, Paper


class BioRxivFetcher(BaseFetcher):
    """
    Fetches preprints from bioRxiv or medRxiv.

    Args:
        search_terms:  keywords to match against title + abstract (client-side)
        server:        "biorxiv" or "medrxiv"
        categories:    optional allow-list of subject categories, e.g.
                       ["neuroscience", "genomics"] for bioRxiv, or
                       ["neurology", "radiology"] for medRxiv.
                       Pass None to skip category filtering.
        days_lookback: how many days back to query
        max_results:   cap on papers returned after filtering
    """

    BASE_URL = "https://api.biorxiv.org/details"

    def __init__(
        self,
        search_terms: list[str],
        server: str = "biorxiv",
        categories: list[str] | None = None,
        days_lookback: int = 1,
        max_results: int = 30,
    ):
        if server not in ("biorxiv", "medrxiv"):
            raise ValueError("server must be 'biorxiv' or 'medrxiv'")
        self.search_terms = [t.lower() for t in search_terms]
        self.server = server
        self.categories = {c.lower() for c in categories} if categories else None
        self.days_lookback = days_lookback
        self.max_results = max_results

    @property
    def source_name(self) -> str:
        return "bioRxiv" if self.server == "biorxiv" else "medRxiv"

    def _matches(self, record: dict) -> bool:
        """Return True if any search term appears in title or abstract."""
        haystack = f"{record.get('title', '')} {record.get('abstract', '')}".lower()
        return any(term in haystack for term in self.search_terms)

    def fetch_papers(self) -> list[Paper]:
        end = datetime.now()
        start = end - timedelta(days=self.days_lookback)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        print(f"[{self.source_name}] Fetching papers from {start_str} to {end_str}...")

        papers: list[Paper] = []
        cursor = 0

        while len(papers) < self.max_results:
            url = f"{self.BASE_URL}/{self.server}/{start_str}/{end_str}/{cursor}/json"
            data = self._fetch_with_retry(url, cursor)
            if data is None:
                break

            records = data.get("collection", [])
            if not records:
                break

            for rec in records:
                # Optional category filter
                if self.categories and rec.get("category", "").lower() not in self.categories:
                    continue
                # Keyword filter (title + abstract)
                if not self._matches(rec):
                    continue

                doi = rec.get("doi", "").strip()
                papers.append(Paper(
                    title=rec.get("title", "").strip(),
                    authors=[
                        a.strip()
                        for a in rec.get("authors", "").split(";")
                        if a.strip()
                    ],
                    abstract=" ".join(rec.get("abstract", "").split()),
                    url=f"https://doi.org/{doi}" if doi else f"https://www.{self.server}.org/",
                    published=rec.get("date", ""),
                    categories=[rec.get("category", "")] if rec.get("category") else [],
                    source=self.server,
                    doi=doi or None,
                ))

                if len(papers) >= self.max_results:
                    break

            # Paginate: each page returns up to 100 records
            messages = data.get("messages", [{}])
            total = int(messages[0].get("total", 0)) if messages else 0
            cursor += len(records)
            if cursor >= total:
                break

        print(f"[{self.source_name}] Found {len(papers)} paper(s) matching search terms.")
        return papers

    def _fetch_with_retry(
        self,
        url: str,
        cursor: int,
        max_retries: int = 3,
        timeout: int = 20,
    ) -> dict | None:
        """GET *url* with exponential backoff. Returns parsed JSON or None on failure."""
        for attempt in range(1, max_retries + 1):
            try:
                with urllib.request.urlopen(url, timeout=timeout, context=get_ssl_context()) as resp:
                    return json.loads(resp.read())
            except Exception as exc:
                if attempt == max_retries:
                    if cursor == 0:
                        print(f"[{self.source_name}] Request failed after {max_retries} attempts: {exc}")
                    else:
                        print(
                            f"[{self.source_name}] Pagination stopped early at cursor {cursor} "
                            f"after {max_retries} attempts: {exc}"
                        )
                    return None
                wait = 2 ** attempt  # 2s, 4s
                print(f"[{self.source_name}] Attempt {attempt} failed (cursor={cursor}, {exc}). Retrying in {wait}s…")
                time.sleep(wait)
        return None  # unreachable, but satisfies type checker
