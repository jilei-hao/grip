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
