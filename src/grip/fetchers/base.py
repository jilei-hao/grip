"""
Base class for all GRIP fetchers.
Every fetcher must implement fetch_papers() and return list[Paper].
This is the contract that keeps the pipeline source-agnostic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Paper:
    title: str
    authors: list[str]
    abstract: str
    url: str
    published: str       # ISO date string: "YYYY-MM-DD"
    categories: list[str]
    source: str          # "arxiv" | "semantic_scholar" | "rss" | ...
    doi: str | None = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "url": self.url,
            "published": self.published,
            "categories": self.categories,
            "source": self.source,
            "doi": self.doi,
        }

    def dedup_key(self) -> str:
        """Canonical key for deduplication. DOI preferred, title as fallback."""
        if self.doi:
            return self.doi.lower().strip()
        return self.title.lower().strip()

    def to_prompt_str(self) -> str:
        """Formatted string to include in Claude scoring prompt."""
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += " et al."
        return (
            f"Title: {self.title}\n"
            f"Authors: {authors_str}\n"
            f"Published: {self.published} | Source: {self.source}\n"
            f"URL: {self.url}\n"
            f"Abstract: {self.abstract}\n"
        )


class BaseFetcher(ABC):
    """Abstract base class all fetchers must inherit from."""

    @abstractmethod
    def fetch_papers(self) -> list[Paper]:
        """Fetch and return a list of Paper objects."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name for this source, e.g. 'arXiv'."""
        ...
