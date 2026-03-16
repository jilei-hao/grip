"""
GRIP — Feedback Collector
Logs Slack emoji reactions (👍/👎) on digest messages to JSONL files.

Polling (pull):
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

THUMBS_UP = "+1"
THUMBS_DOWN = "-1"

_SLACK_REACTIONS_GET = "https://slack.com/api/reactions.get"
_SLACK_REPLIES = "https://slack.com/api/conversations.replies"


class FeedbackCollector:

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()
        self._log_dir = self._settings.feedback_log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def handle_reaction(self, *args, **kwargs) -> int:
        """
        Deprecated compatibility shim for the old event-driven feedback API.

        The previous implementation accepted individual reaction events.
        The collector now works in polling mode via :meth:`poll_feedback`.

        This method is kept only to avoid AttributeError in older tests or
        callers. It raises a RuntimeError to clearly indicate that the
        event-based API has been removed and that callers should be updated
        to use :meth:`poll_feedback` instead.
        """
        raise RuntimeError(
            "FeedbackCollector.handle_reaction() has been removed. "
            "Use FeedbackCollector.poll_feedback(token, channel) instead."
        )

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

        # Cache thread replies per header_ts to avoid redundant API calls.
        # Paper messages are replies in the header's thread, so we must fetch
        # conversations.replies using header_ts (the thread root), not paper_ts.
        thread_comments_cache: dict[str, list[str]] = {}

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
            # Papers are posted as replies in the header's thread, so thread
            # replies must be fetched using header_ts (the thread root), not
            # the individual paper_ts which is not a thread root.
            header_ts = paper.get("header_ts") or paper_ts
            if header_ts not in thread_comments_cache:
                comments_for_thread: list[str] = []
                replies_body = self._api_get(token, _SLACK_REPLIES, {
                    "channel": paper_channel,
                    "ts": header_ts,
                })
                if replies_body:
                    for msg in replies_body.get("messages", []):
                        # Skip the root message and bot messages
                        if msg.get("ts") == header_ts:
                            continue
                        if msg.get("bot_id") or msg.get("subtype") == "bot_message":
                            continue
                        text = msg.get("text", "").strip()
                        if text:
                            comments_for_thread.append(text)
                thread_comments_cache[header_ts] = comments_for_thread
            comments = thread_comments_cache[header_ts]

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

        # ── Standalone thread comments (one entry per digest, deduped) ─────────
        # Load already-logged header_ts values to avoid re-saving on repeated polls.
        already_logged_headers = {
            e.get("header_ts")
            for e in self.load_recent()
            if e.get("event_type") == "thread_comment"
        }
        for hts, comments in thread_comments_cache.items():
            if not comments or hts in already_logged_headers:
                continue
            self._append({
                "timestamp": datetime.now().isoformat(),
                "event_type": "thread_comment",
                "header_ts": hts,
                "comments": list(dict.fromkeys(comments)),  # preserve order, dedupe
            })
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
