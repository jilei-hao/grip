"""
GRIP — arXiv Fetcher
Implements BaseFetcher for the arXiv API (no API key required).
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from grip.fetchers.base import BaseFetcher, Paper


class ArxivFetcher(BaseFetcher):

    source_name = "arXiv"

    def __init__(self, search_terms: list[str], max_results: int = 30, days_lookback: int = 1):
        self.search_terms = search_terms
        self.max_results = max_results
        self.days_lookback = days_lookback

    def _build_query(self) -> str:
        parts = [f'(ti:"{term}" OR abs:"{term}")' for term in self.search_terms]
        return " OR ".join(parts)

    def fetch_papers(self) -> list[Paper]:
        query = self._build_query()
        cutoff = datetime.now() - timedelta(days=self.days_lookback)

        params = urllib.parse.urlencode({
            "search_query": query,
            "start": 0,
            "max_results": self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        })

        url = f"http://export.arxiv.org/api/query?{params}"
        print(f"[arXiv] Fetching papers...")

        with urllib.request.urlopen(url) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        papers = []
        for entry in root.findall("atom:entry", ns):
            pub_raw = entry.find("atom:published", ns).text
            pub_dt = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
            if pub_dt.replace(tzinfo=None) < cutoff:
                continue

            authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
            categories = [t.get("term") for t in entry.findall("atom:category", ns)]
            abstract = " ".join((entry.find("atom:summary", ns).text or "").split())
            doi_el = entry.find("arxiv:doi", ns)

            papers.append(Paper(
                title=entry.find("atom:title", ns).text.strip(),
                authors=authors,
                abstract=abstract,
                url=entry.find("atom:id", ns).text.strip(),
                published=pub_dt.strftime("%Y-%m-%d"),
                categories=categories,
                source="arxiv",
                doi=doi_el.text.strip() if doi_el is not None else None,
            ))

        print(f"[arXiv] Found {len(papers)} paper(s).")
        return papers
