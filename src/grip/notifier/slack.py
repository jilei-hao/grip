"""
GRIP — Slack Notifier
Posts the daily digest to Slack.

Two modes (selected automatically):

  Threaded  [preferred]
    Requires: GRIP_SLACK_BOT_TOKEN  (xoxb-…)
              GRIP_SLACK_CHANNEL_ID (C01234ABCDE)
    Behaviour:
      1. Posts a compact header message listing all paper titles to the channel.
      2. Posts each paper as a threaded reply, with its summary and score.
      3. Users react 👍 / 👎 on individual thread replies → per-paper feedback.

  Webhook fallback
    Requires: GRIP_SLACK_WEBHOOK
    Behaviour: Posts a single compact message (no threading, no per-paper reactions).
"""

from __future__ import annotations

import json
import urllib.request
from urllib.error import URLError

from grip.config import Settings, get_ssl_context, load_settings
from grip.notifier.formatter import format_digest, format_digest_header, format_paper_block

_SLACK_API = "https://slack.com/api/chat.postMessage"


class SlackNotifier:

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()

    def post_digest(self, selected_papers: list[dict]) -> bool:
        """Post formatted digest to Slack. Returns True on success."""
        token = self._settings.slack_bot_token
        channel = self._settings.slack_channel_id

        if token and channel:
            return self._post_threaded(selected_papers, token, channel)

        # Fallback: single webhook post
        return self._post_webhook(selected_papers)

    # ── Threaded (Web API) ────────────────────────────────────────────────────

    def _post_threaded(self, papers: list[dict], token: str, channel: str) -> bool:
        """
        Post header to channel, then each paper as a thread reply.
        Uses the Slack Web API (chat.postMessage) with Authorization header.
        """
        # 1. Post header; capture ts for threading
        header_blocks = format_digest_header(papers)
        ts = self._api_post(token, channel, header_blocks, thread_ts=None)
        if ts is None:
            print("[slack] Failed to post digest header.")
            return False

        # 2. Post each paper as a thread reply
        failures = 0
        for i, paper in enumerate(papers, 1):
            blocks = format_paper_block(paper, i)
            reply_ts = self._api_post(token, channel, blocks, thread_ts=ts)
            if reply_ts is None:
                print(f"[slack] Failed to post paper {i} to thread.")
                failures += 1

        ok_count = len(papers) - failures
        print(f"[slack] Threaded digest posted: {ok_count}/{len(papers)} papers in thread.")
        return failures == 0

    def _api_post(
        self,
        token: str,
        channel: str,
        blocks: list[dict],
        thread_ts: str | None,
    ) -> str | None:
        """
        Call chat.postMessage. Returns the message ts on success, None on failure.
        """
        payload: dict = {"channel": channel, "blocks": blocks}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            _SLACK_API,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        try:
            with urllib.request.urlopen(req, context=get_ssl_context()) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                if body.get("ok"):
                    return body["ts"]
                print(f"[slack] API error: {body.get('error', 'unknown')}")
                return None
        except URLError as exc:
            print(f"[slack] Request failed: {exc}")
            return None

    # ── Webhook fallback ──────────────────────────────────────────────────────

    def _post_webhook(self, papers: list[dict]) -> bool:
        """Post a single compact message via Incoming Webhook."""
        blocks = format_digest(papers)
        payload = json.dumps({"blocks": blocks}).encode("utf-8")

        req = urllib.request.Request(
            self._settings.slack_webhook,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, context=get_ssl_context()) as resp:
                if resp.status == 200:
                    print(f"[slack] Webhook: posted {len(papers)} papers.")
                    return True
                print(f"[slack] Webhook failed with status {resp.status}.")
                return False
        except URLError as exc:
            print(f"[slack] Webhook request failed: {exc}")
            return False
