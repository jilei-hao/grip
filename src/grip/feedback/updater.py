"""
GRIP — Profile Updater
Core of the learning loop: uses accumulated 👍/👎 feedback (and text comments)
to update the interest profile via Claude. Run weekly, not daily.
"""

from __future__ import annotations

import anthropic

from grip.config import Settings, get_httpx_client, load_settings
from grip.feedback.collector import FeedbackCollector
from grip.profile.manager import ProfileManager
from grip.scorer.prompts import PROFILE_UPDATE_PROMPT


def _is_positive(f: dict) -> bool:
    if f.get("event_type") == "reaction_poll":
        return f.get("thumbsup", 0) > f.get("thumbsdown", 0)
    return f.get("sentiment") == "positive"


def _is_negative(f: dict) -> bool:
    if f.get("event_type") == "reaction_poll":
        return f.get("thumbsdown", 0) > f.get("thumbsup", 0)
    return f.get("sentiment") == "negative"


def _format_feedback_block(entries: list[dict]) -> str:
    """
    Render a list of feedback entries into a human-readable block for Claude.
    Handles both legacy reaction_added entries and new reaction_poll entries.
    """
    if not entries:
        return "(none)"

    lines: list[str] = []
    for f in entries:
        if f.get("event_type") == "reaction_poll":
            title = f.get("paper_title") or "(unknown title)"
            url = f.get("paper_url", "")
            up = f.get("thumbsup", 0)
            down = f.get("thumbsdown", 0)
            comments = f.get("comments", [])

            line = f'- "{title}"'
            if url:
                line += f" ({url})"
            line += f"\n  Reactions: {up} 👍, {down} 👎"
            if comments:
                quoted = ", ".join(f'"{c}"' for c in comments)
                line += f"\n  Comments: {quoted}"
            lines.append(line)
        else:
            # Legacy entry: show message_ts as fallback identifier
            ts = f.get("message_ts", "unknown")
            lines.append(f"- Message ts: {ts} ({f.get('sentiment', '?')})")

    return "\n".join(lines)


class ProfileUpdater:

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()
        self._collector = FeedbackCollector(self._settings)
        self._profile = ProfileManager(self._settings)
        self._client = anthropic.Anthropic(
            api_key=self._settings.anthropic_api_key,
            http_client=get_httpx_client(),
        )

    def run_update(self) -> bool:
        """
        Pull recent feedback and update the profile if enough signal exists.
        Returns True if profile was updated, False if skipped (too little feedback).
        """
        # ── Poll Slack for fresh feedback if bot token is available ───────────
        token = self._settings.slack_bot_token
        channel = self._settings.slack_channel_id
        if token and channel:
            print("[updater] Polling Slack for fresh feedback...")
            self._collector.poll_feedback(token=token, channel=channel)
        else:
            print("[updater] No bot token/channel configured; using cached feedback only.")

        # ── Load and threshold-check ──────────────────────────────────────────
        feedback = self._collector.load_recent()
        min_count = self._settings.min_feedback_to_update

        if len(feedback) < min_count:
            print(
                f"[updater] {len(feedback)} feedback entries found, need {min_count}. Skipping."
            )
            return False

        positive = [f for f in feedback if _is_positive(f)]
        negative = [f for f in feedback if _is_negative(f)]
        thread_comments = [f for f in feedback if f.get("event_type") == "thread_comment"]

        # Flatten and deduplicate general comments across all thread_comment entries
        seen: set[str] = set()
        general: list[str] = []
        for entry in thread_comments:
            for c in entry.get("comments", []):
                if c not in seen:
                    seen.add(c)
                    general.append(c)

        general_comments_block = (
            "\n".join(f'- "{c}"' for c in general) if general else "(none)"
        )

        print(
            f"[updater] Updating profile from {len(feedback)} feedback entries "
            f"({len(positive)} 👍, {len(negative)} 👎, {len(general)} general comments)..."
        )

        prompt = PROFILE_UPDATE_PROMPT.format(
            current_profile=self._profile.load(),
            thumbs_up_papers=_format_feedback_block(positive),
            thumbs_down_papers=_format_feedback_block(negative),
            general_comments=general_comments_block,
        )

        response = self._client.messages.create(
            model=self._settings.profile_update_model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        new_profile = response.content[0].text.strip()
        self._profile.save(
            new_profile,
            reason=f"feedback update ({len(feedback)} entries)"
        )
        return True
