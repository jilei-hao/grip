"""
GRIP — Configuration via environment variables.

All settings have sensible defaults. Override in .env or shell environment.
The Settings class is a simple dataclass — no magic, easy to inspect and test.
"""

from __future__ import annotations

import os
import ssl
import httpx
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _load_dotenv() -> None:
    """Search for a .env file starting from the current working directory,
    then from a 'grip/' subdirectory within it (the layout used by grip-stg).
    Does not override variables that are already set in the shell environment."""
    for candidate in (
        Path.cwd() / ".env",
        Path.cwd() / "grip" / ".env",
    ):
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return


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

    @property
    def ncbi_api_key(self) -> str | None:
        """Optional NCBI API key. Raises the E-utilities rate limit from 3 to
        10 requests/second. Get one free at https://www.ncbi.nlm.nih.gov/account/
        Set NCBI_API_KEY in environment or .env file."""
        return os.environ.get("NCBI_API_KEY") or None


def load_settings() -> Settings:
    """Load settings from environment variables (and .env if present)."""
    _load_dotenv()
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


def get_ssl_context() -> ssl.SSLContext:
    """Return an SSL context for outbound HTTPS requests.

    By default, certificate verification is enabled. If your network uses a
    proxy that performs SSL inspection (corporate MITM proxy), certificate
    verification will fail with 'self-signed certificate in certificate chain'.
    Set GRIP_SSL_VERIFY=false in your environment or .env to disable it.
    """
    ctx = ssl.create_default_context()
    if os.environ.get("GRIP_SSL_VERIFY", "true").strip().lower() in ("false", "0", "no"):
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def get_httpx_client() -> httpx.Client | None:
    """Return a custom httpx.Client with SSL verification disabled when
    GRIP_SSL_VERIFY=false, or None to let the caller use the default client."""
    if os.environ.get("GRIP_SSL_VERIFY", "true").strip().lower() in ("false", "0", "no"):
        return httpx.Client(verify=False)
    return None
