"""
GRIP — Semantic Scholar Fetcher (stub)
Uses Semantic Scholar API. Free tier: 100 req/5min unauthenticated,
or higher with API key.
https://api.semanticscholar.org/
"""

from grip.fetchers.base import BaseFetcher, Paper


class SemanticScholarFetcher(BaseFetcher):
    """
    TODO: Implement when ready to add a second source.

    Semantic Scholar API endpoint:
    GET https://api.semanticscholar.org/graph/v1/paper/search
    Params: query, fields, limit, publicationDateOrYear

    API key (optional, increases rate limits):
    Set SEMANTIC_SCHOLAR_API_KEY in .env
    """

    source_name = "Semantic Scholar"

    def __init__(self, search_terms: list[str], days_lookback: int = 1, api_key: str | None = None):
        self.search_terms = search_terms
        self.days_lookback = days_lookback
        self.api_key = api_key

    def fetch_papers(self) -> list[Paper]:
        raise NotImplementedError("SemanticScholarFetcher not yet implemented.")
