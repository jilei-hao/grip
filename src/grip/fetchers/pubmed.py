"""
GRIP — PubMed Fetcher
Uses NCBI E-utilities API (no API key required for light usage).
Set NCBI_API_KEY in environment to raise the rate limit from 3 to 10 req/s.

API docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/

Two-step process:
  1. esearch — get a list of PMIDs matching query + date range
  2. efetch  — retrieve full XML records (title, abstract, authors, DOI)
"""

import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

from grip.config import get_ssl_context
from grip.fetchers.base import BaseFetcher, Paper

# Month abbreviations used in PubMed XML dates
_MONTH_ABBR = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}


class PubMedFetcher(BaseFetcher):
    """
    Fetches articles from PubMed via NCBI E-utilities.

    Args:
        search_terms:  keywords searched in Title/Abstract fields
        days_lookback: look back this many days using reldate filter
        max_results:   maximum number of articles to return
        api_key:       optional NCBI API key (increases rate limit to 10 req/s).
                       Falls back to the NCBI_API_KEY environment variable.
    """

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    source_name = "pubmed"

    def __init__(
        self,
        search_terms: list[str],
        days_lookback: int = 1,
        max_results: int = 30,
        api_key: str | None = None,
    ):
        self.search_terms = search_terms
        self.days_lookback = days_lookback
        self.max_results = max_results
        self.api_key = api_key or os.environ.get("NCBI_API_KEY") or None

    def _build_query(self) -> str:
        parts = [f'("{t}"[Title/Abstract])' for t in self.search_terms]
        return " OR ".join(parts)

    def _parse_date(self, pub_date_el: ET.Element | None) -> str:
        """Convert a PubMed <PubDate> element to YYYY-MM-DD string."""
        if pub_date_el is None:
            return ""
        year  = pub_date_el.findtext("Year", "")
        month = pub_date_el.findtext("Month", "01")
        day   = pub_date_el.findtext("Day",   "01")
        # Month may be numeric ("3") or abbreviated ("Mar")
        month = _MONTH_ABBR.get(month, month).zfill(2)
        day   = day.zfill(2)
        try:
            return datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return year  # fall back to year-only

    def fetch_papers(self) -> list[Paper]:
        print("[PubMed] Fetching papers...")
        query = self._build_query()

        # ── Step 1: esearch ───────────────────────────────────────────────────
        search_params: dict = {
            "db":       "pubmed",
            "term":     query,
            "datetype": "pdat",
            "reldate":  self.days_lookback,
            "retmax":   self.max_results,
            "retmode":  "json",
        }
        if self.api_key:
            search_params["api_key"] = self.api_key

        search_url = f"{self.ESEARCH_URL}?{urllib.parse.urlencode(search_params)}"
        try:
            with urllib.request.urlopen(search_url, timeout=15, context=get_ssl_context()) as resp:
                search_data = json.loads(resp.read())
        except Exception as exc:
            print(f"[PubMed] esearch failed: {exc}")
            return []

        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            print("[PubMed] No results found.")
            return []

        # ── Step 2: efetch ────────────────────────────────────────────────────
        fetch_params: dict = {
            "db":      "pubmed",
            "id":      ",".join(pmids),
            "retmode": "xml",
        }
        if self.api_key:
            fetch_params["api_key"] = self.api_key

        fetch_url = f"{self.EFETCH_URL}?{urllib.parse.urlencode(fetch_params)}"
        try:
            with urllib.request.urlopen(fetch_url, timeout=30, context=get_ssl_context()) as resp:
                xml_data = resp.read()
        except Exception as exc:
            print(f"[PubMed] efetch failed: {exc}")
            return []

        root = ET.fromstring(xml_data)
        papers: list[Paper] = []

        for article in root.findall(".//PubmedArticle"):
            medline = article.find("MedlineCitation")
            if medline is None:
                continue
            art = medline.find("Article")
            if art is None:
                continue

            # Title (may contain nested markup)
            title_el = art.find("ArticleTitle")
            title = "".join(title_el.itertext()).strip() if title_el is not None else ""
            if not title:
                continue

            # Abstract (may have multiple structured sections)
            abstract_parts = art.findall(".//AbstractText")
            abstract = " ".join("".join(el.itertext()) for el in abstract_parts).strip()
            abstract = " ".join(abstract.split())

            # Authors
            authors: list[str] = []
            for author in art.findall(".//Author"):
                last = author.findtext("LastName", "")
                fore = author.findtext("ForeName", "")
                collective = author.findtext("CollectiveName", "")
                name = f"{fore} {last}".strip() if (fore or last) else collective
                if name:
                    authors.append(name)

            # Published date
            pub_date_el = art.find(".//PubDate")
            published = self._parse_date(pub_date_el)

            # PMID
            pmid = medline.findtext("PMID", "").strip()
            url  = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "https://pubmed.ncbi.nlm.nih.gov/"

            # DOI
            doi: str | None = None
            for id_el in article.findall(".//ArticleId"):
                if id_el.get("IdType") == "doi" and id_el.text:
                    doi = id_el.text.strip()
                    break

            # MeSH categories
            categories = [
                mh.findtext("DescriptorName", "")
                for mh in medline.findall(".//MeshHeading")
            ]
            categories = [c for c in categories if c]

            papers.append(Paper(
                title=title,
                authors=authors,
                abstract=abstract,
                url=url,
                published=published,
                categories=categories,
                source="pubmed",
                doi=doi,
            ))

        print(f"[PubMed] Found {len(papers)} paper(s).")
        return papers
