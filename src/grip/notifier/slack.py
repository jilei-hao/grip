"""
GRIP — Slack Notifier
Posts the daily digest to Slack via Incoming Webhook.
"""

from __future__ import annotations

import json
import urllib.request

from grip.config import Settings, load_settings
from grip.notifier.formatter import format_digest


class SlackNotifier:

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()

    def post_digest(self, selected_papers: list[dict]) -> bool:
        """Post formatted digest to Slack. Returns True on success."""
        blocks = format_digest(selected_papers)
        payload = json.dumps({"blocks": blocks}).encode("utf-8")

        req = urllib.request.Request(
            self._settings.slack_webhook,
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                print(f"[slack] Posted {len(selected_papers)} papers successfully.")
                return True
            print(f"[slack] Failed with status {resp.status}.")
            return False
