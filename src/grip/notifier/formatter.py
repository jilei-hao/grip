"""
GRIP — Slack Message Formatter
Converts scored papers into Slack Block Kit messages.

Two posting modes are supported:

  Threaded (preferred, requires bot token + channel ID)
  ───────────────────────────────────────────────────
  • format_digest_header()  → compact channel post: numbered title list
  • format_paper_block()    → one thread reply per paper, with summary
                              collapsed behind Slack's native "Show more"
    Users react 👍 / 👎 on each thread reply independently.

  Webhook fallback
  ────────────────
  • format_digest()         → single compact post, full content, no threading
"""

from datetime import datetime


# ── Threading mode ────────────────────────────────────────────────────────────

def format_digest_header(selected_papers: list[dict], date: str | None = None) -> list[dict]:
    """
    Compact *channel* post: one numbered line per paper, inviting readers into
    the thread for details and to leave feedback reactions.
    """
    date = date or datetime.now().strftime("%B %d, %Y")

    # Build a numbered title list (plain text — no links to avoid URL preview expansion)
    lines = "\n".join(
        f"{i}. {p['title']}"
        for i, p in enumerate(selected_papers, 1)
    )

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📚 GRIP Daily Digest — {date}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": lines},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*{len(selected_papers)} paper{'s' if len(selected_papers) != 1 else ''}* matched your profile"
                        " · Open the thread 🧵 to read summaries and react 👍 👎 on each paper"
                    ),
                }
            ],
        },
    ]


def format_paper_block(paper: dict, index: int) -> list[dict]:
    """
    Blocks for a *single* paper posted as a thread reply.

    Layout (top → bottom):
      • Title (linked, bold) + relevance reason on the same section
      • Score badge in a context block
      • Summary — placed in its own section so Slack's automatic "Show more"
        collapses it when it exceeds ~700 chars, giving a native expand/collapse.
      • Divider
    """
    score = paper.get("relevance_score", "?")
    reason = paper.get("relevance_reason", "").strip()
    summary = paper.get("summary", "").strip()

    blocks: list[dict] = [
        {"type": "divider"},
        # Title + reason
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{index}. <{paper['url']}|{paper['title']}>*"
                + (f"\n_{reason}_" if reason else ""),
            },
        },
        # Score
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Relevance: *{score}/10* · React 👍 or 👎 to give feedback",
                }
            ],
        },
    ]

    # Summary goes in a separate section so Slack auto-collapses long text.
    # A short header line ensures the key info stays visible even when collapsed.
    if summary:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Summary*\n{summary}",
            },
        })

    blocks.append({"type": "divider"})
    return blocks


def format_feed_explanation(
    profile: str,
    selection_notes: str = "",
) -> list[dict]:
    """
    Final thread reply explaining why today's papers were selected.
    Incorporates the group interest profile and scorer notes.
    Surfaces any feedback-driven profile updates if a changelog line is present.
    """
    # Extract key profile themes: first non-empty lines up to ~300 chars
    profile_lines = [l.strip() for l in profile.strip().splitlines() if l.strip()]

    # Detect feedback changelog (e.g. "Updated YYYY-MM-DD: ...")
    changelog_lines = [l for l in profile_lines if l.lower().startswith("updated ")]
    latest_update = changelog_lines[-1] if changelog_lines else None

    # Build a short profile excerpt (skip changelog lines, cap at ~250 chars)
    excerpt_parts: list[str] = []
    total = 0
    for line in profile_lines:
        if line.lower().startswith("updated "):
            continue
        if total + len(line) > 250:
            break
        excerpt_parts.append(line)
        total += len(line)
    profile_excerpt = " ".join(excerpt_parts)
    if len(profile_excerpt) < len(" ".join(
        l for l in profile_lines if not l.lower().startswith("updated ")
    )):
        profile_excerpt += "…"

    text_parts = ["*🔍 Why these papers?*"]
    text_parts.append(f"_Profile:_ {profile_excerpt}")
    if selection_notes:
        text_parts.append(f"_Today's batch:_ {selection_notes}")
    if latest_update:
        text_parts.append(f"_Profile last refined from feedback:_ {latest_update}")
    text_parts.append("\nReact 👍 or 👎 on any paper above — your feedback shapes future digests.")

    return [
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(text_parts)},
        },
    ]


# ── Webhook fallback (single post) ────────────────────────────────────────────

def format_digest(selected_papers: list[dict], date: str | None = None) -> list[dict]:
    """
    Single-post format for webhook delivery (no threading available).
    Keeps each entry compact: title + reason + score, no full summary,
    to minimise post length.
    """
    date = date or datetime.now().strftime("%B %d, %Y")
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📚 GRIP Daily Digest — {date}"},
        },
        {"type": "divider"},
    ]

    for i, paper in enumerate(selected_papers, 1):
        score = paper.get("relevance_score", "?")
        reason = paper.get("relevance_reason", "").strip()

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{i}. <{paper['url']}|{paper['title']}>*"
                + (f"\n_{reason}_" if reason else ""),
            },
        })
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Score: *{score}/10* · React 👍 👎 to give feedback",
                }
            ],
        })
        blocks.append({"type": "divider"})

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "GRIP · Your reactions help improve future selections"}],
    })
    return blocks
