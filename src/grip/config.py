"""
GRIP — Configuration via environment variables.

All settings have sensible defaults. Override in .env or shell environment.
The Settings class is a simple dataclass — no magic, easy to inspect and test.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_list(key: str, default: list[str]) -> list[str]:
    """Parse a comma-separated env var into a list, falling back to default."""
    raw = os.environ.get(key, "")
    return [x.strip() for x in raw.split(",") if x.strip()] or default


@dataclass
class Settings:
    # ── Sources ───────────────────────────────────────────────────────────────
    search_terms: list[str] = field(default_factory=lambda: ["machine learning"])
    days_lookback: int = 1
    max_fetch_per_source: int = 30

    # ── Scoring ───────────────────────────────────────────────────────────────
    top_n_papers: int = 5
    scoring_model: str = "claude-haiku-4-5-20251001"
    profile_update_model: str = "claude-sonnet-4-6"

    # ── Feedback ──────────────────────────────────────────────────────────────
    feedback_window_days: int = 7
    min_feedback_to_update: int = 5

    # ── Paths ─────────────────────────────────────────────────────────────────
    # Default to package-bundled data dir; user can override to a custom path
    data_dir: Path = field(
        default_factory=lambda: Path(os.environ.get(
            "GRIP_DATA_DIR",
            str(Path(__file__).parent / "data")
        ))
    )

    @property
    def profile_path(self) -> Path:
        return self.data_dir / "interest_profile.txt"

    @property
    def feedback_log_dir(self) -> Path:
        return self.data_dir / "feedback_log"

    @property
    def profile_versions_dir(self) -> Path:
        return self.data_dir / "profile_versions"

    # ── Secrets ───────────────────────────────────────────────────────────────
    @property
    def anthropic_api_key(self) -> str:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")
        return key

    @property
    def slack_webhook(self) -> str:
        url = os.environ.get("GRIP_SLACK_WEBHOOK", "")
        if not url:
            raise EnvironmentError("GRIP_SLACK_WEBHOOK environment variable is not set.")
        return url

    @property
    def slack_bot_token(self) -> str | None:
        """Optional Slack bot token for threaded posting (xoxb-…).
        When set alongside slack_channel_id, enables per-paper thread replies
        so users can react to each paper individually."""
        return os.environ.get("GRIP_SLACK_BOT_TOKEN") or None

    @property
    def slack_channel_id(self) -> str | None:
        """Slack channel ID (e.g. C01234ABCDE) used with slack_bot_token."""
        return os.environ.get("GRIP_SLACK_CHANNEL_ID") or None


def load_settings() -> Settings:
    """Load settings from environment variables."""
    return Settings(
        search_terms=_env_list("GRIP_SEARCH_TERMS", ["machine learning"]),
        days_lookback=int(os.environ.get("GRIP_DAYS_LOOKBACK", "1")),
        max_fetch_per_source=int(os.environ.get("GRIP_MAX_FETCH", "30")),
        top_n_papers=int(os.environ.get("GRIP_TOP_N", "5")),
        scoring_model=os.environ.get("GRIP_SCORING_MODEL", "claude-haiku-4-5-20251001"),
        profile_update_model=os.environ.get("GRIP_UPDATE_MODEL", "claude-sonnet-4-6"),
        feedback_window_days=int(os.environ.get("GRIP_FEEDBACK_DAYS", "7")),
        min_feedback_to_update=int(os.environ.get("GRIP_MIN_FEEDBACK", "5")),
    )
