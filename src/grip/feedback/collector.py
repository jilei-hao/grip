"""
GRIP — Feedback Collector
Logs Slack emoji reactions (👍/👎) on digest messages to JSONL files.

How it works:
- Each digest post has a Slack message timestamp (ts)
- Users react with 👍 or 👎
- Slack Events API sends reaction_added/removed events to your endpoint
- This class handles those events and logs them to daily JSONL files

Deployment options for the events endpoint:
- Local dev: ngrok tunnel → Flask server
- Production: AWS Lambda + API Gateway, or any small VPS
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from grip.config import Settings, load_settings

THUMBS_UP = "thumbsup"
THUMBS_DOWN = "thumbsdown"


class FeedbackCollector:

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()
        self._log_dir = self._settings.feedback_log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def handle_reaction(self, event: dict) -> None:
        """
        Process a Slack reaction_added or reaction_removed event.

        Expected event shape (Slack Events API):
        {
            "type": "reaction_added" | "reaction_removed",
            "reaction": "thumbsup" | "thumbsdown",
            "item": {"ts": "<message_timestamp>"},
            "user": "<slack_user_id>"
        }
        """
        reaction = event.get("reaction")
        if reaction not in (THUMBS_UP, THUMBS_DOWN):
            return  # ignore all other reactions

        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event.get("type"),
            "reaction": reaction,
            "message_ts": event.get("item", {}).get("ts"),
            "user": event.get("user"),
            "sentiment": "positive" if reaction == THUMBS_UP else "negative",
        }
        self._append(entry)
        print(f"[feedback] Logged {entry['sentiment']} reaction on {entry['message_ts']}")

    def load_recent(self, days: int | None = None) -> list[dict]:
        """Load all feedback entries from the last N days."""
        window = days or self._settings.feedback_window_days
        entries: list[dict] = []
        for i in range(window):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            log_path = self._log_dir / f"{date}.jsonl"
            if log_path.exists():
                with log_path.open(encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entries.append(json.loads(line))
        return entries

    def _append(self, entry: dict) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = self._log_dir / f"{today}.jsonl"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
