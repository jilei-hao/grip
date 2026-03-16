"""
GRIP — Digest Registry
Persists a mapping of Slack message timestamps → paper metadata,
written once per daily digest run. Used by FeedbackCollector to look up
which Slack message corresponds to which paper when polling reactions.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from grip.config import Settings, load_settings


class DigestRegistry:

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()
        self._log_dir = self._settings.digest_log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        header_ts: str,
        channel: str,
        papers: list[dict],
        date: str | None = None,
    ) -> None:
        """
        Write today's digest registry to data/digest_log/YYYY-MM-DD.json.
        Overwrites any previous registry for the same date (idempotent on reruns).

        papers: list of {ts, title, url, relevance_score} dicts
        """
        date = date or datetime.now().strftime("%Y-%m-%d")
        record = {
            "date": date,
            "header_ts": header_ts,
            "channel": channel,
            "papers": papers,
        }
        path = self._log_dir / f"{date}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"[registry] Saved digest registry for {date} ({len(papers)} papers).")

    def load(self, date: str | None = None) -> dict | None:
        """Load registry for a specific date (defaults to today). Returns None if not found."""
        date = date or datetime.now().strftime("%Y-%m-%d")
        path = self._log_dir / f"{date}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_recent(self, days: int | None = None) -> list[dict]:
        """
        Load all registry entries from the last N days.
        Returns a flat list of paper dicts, each augmented with 'channel' and 'date'.
        """
        window = days or self._settings.feedback_window_days
        papers: list[dict] = []
        for i in range(window):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            record = self.load(date)
            if record is None:
                continue
            channel = record.get("channel", "")
            header_ts = record.get("header_ts", "")
            for p in record.get("papers", []):
                papers.append({**p, "channel": channel, "date": date, "header_ts": header_ts})
        return papers
