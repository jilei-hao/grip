"""
GRIP — RSS Fetcher (stub)
For journal RSS feeds, blog feeds, Google Scholar alerts, etc.
Requires: pip install feedparser
"""

from grip.fetchers.base import BaseFetcher, Paper


class RSSFetcher(BaseFetcher):
    """
    TODO: Implement when ready.

    Good RSS sources to consider:
    - Nature: https://www.nature.com/nature.rss
    - Science: https://www.science.org/rss/news_current.xml
    - Google Scholar alerts (personal RSS per alert)
    - Lab/group blogs
    """

    source_name = "RSS"

    def __init__(self, feed_urls: list[str], days_lookback: int = 1):
        self.feed_urls = feed_urls
        self.days_lookback = days_lookback

    def fetch_papers(self) -> list[Paper]:
        raise NotImplementedError("RSSFetcher not yet implemented.")
