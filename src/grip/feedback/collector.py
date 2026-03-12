"""
GRIP — Feedback Collector
Logs Slack emoji reactions (👍/👎) on digest messages to JSONL files.

Two collection modes:

  Event-driven (push):
    Each digest post has a Slack message timestamp (ts).
    Users react with 👍 or 👎.
    Slack Events API sends reaction_added/removed events to your endpoint.
    call handle_reaction() to log those events.
    Deployment options: ngrok tunnel → Flask server, or AWS Lambda + API Gateway.

  Polling (pull) [preferred, no server required]:
    Call poll_feedback(token, channel) to poll Slack Web API for reactions
    and thread text replies on all papers in the recent digest registry.
    Requires GRIP_SLACK_BOT_TOKEN with reactions:read + channels:history scopes.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import URLError

from grip.config import Settings, get_ssl_context, load_settings
from grip.feedback.digest_registry import DigestRegistry

THUMBS_UP = "thumbsup"
THUMBS_DOWN = "thumbsdown"

_SLACK_REACTIONS_GET = "https://slack.com/api/reactions.get"
_SLACK_REPLIES = "https://slack.com/api/conversations.replies"


class FeedbackCollector:

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()
        self._log_dir = self._settings.feedback_log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)

    # ── Event-driven (push) ───────────────────────────────────────────────────

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

    # ── Polling (pull) ────────────────────────────────────────────────────────

    def poll_feedback(self, token: str, channel: str) -> int:
        """
        Poll Slack for reactions and thread replies on all papers in the
        recent digest registry. Saves enriched entries to the JSONL feedback log.
        Returns the number of entries written.

        Requires bot token with: reactions:read, channels:history
        """
        registry = DigestRegistry(self._settings)
        recent_papers = registry.load_recent()

        if not recent_papers:
            print("[feedback] No digest registry entries found; skipping poll.")
            return 0

        count = 0
        for paper in recent_papers:
            paper_ts = paper.get("ts")
            paper_channel = paper.get("channel") or channel
            if not paper_ts:
                continue

            # ── Reactions ──────────────────────────────────────────────────
            thumbsup = 0
            thumbsdown = 0
            body = self._api_get(token, _SLACK_REACTIONS_GET, {
                "channel": paper_channel,
                "timestamp": paper_ts,
                "full": "true",
            })
            if body:
                for r in body.get("message", {}).get("reactions", []):
                    if r["name"] == THUMBS_UP:
                        thumbsup = r.get("count", 0)
                    elif r["name"] == THUMBS_DOWN:
                        thumbsdown = r.get("count", 0)

            # ── Thread text replies ─────────────────────────────────────────
            comments: list[str] = []
            replies_body = self._api_get(token, _SLACK_REPLIES, {
                "channel": paper_channel,
                "ts": paper_ts,
            })
            if replies_body:
                for msg in replies_body.get("messages", []):
                    # Skip the root message (ts == thread_ts) and bot messages
                    if msg.get("ts") == paper_ts:
                        continue
                    if msg.get("bot_id") or msg.get("subtype") == "bot_message":
                        continue
                    text = msg.get("text", "").strip()
                    if text:
                        comments.append(text)

            # Only write entry if there is at least some signal
            if thumbsup == 0 and thumbsdown == 0 and not comments:
                continue

            entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "reaction_poll",
                "message_ts": paper_ts,
                "paper_title": paper.get("title", ""),
                "paper_url": paper.get("url", ""),
                "thumbsup": thumbsup,
                "thumbsdown": thumbsdown,
                "comments": comments,
            }
            self._append(entry)
            count += 1

        print(f"[feedback] Polled {len(recent_papers)} papers, wrote {count} entries.")
        return count

    # ── Shared ────────────────────────────────────────────────────────────────

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

    def _api_get(self, token: str, url: str, params: dict) -> dict | None:
        """Make a Slack Web API GET request. Returns parsed JSON body or None on failure."""
        query = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        req = urllib.request.Request(
            full_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(req, context=get_ssl_context()) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                if body.get("ok"):
                    return body
                print(f"[feedback] Slack API error ({url.split('/')[-1]}): {body.get('error', 'unknown')}")
                return None
        except URLError as exc:
            print(f"[feedback] Request failed ({url.split('/')[-1]}): {exc}")
            return None
