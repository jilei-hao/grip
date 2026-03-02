"""
GRIP — Slack Message Formatter
Converts scored papers into Slack Block Kit messages.
Block Kit gives rich formatting: headers, dividers, buttons, links.
"""

from datetime import datetime


def format_digest(selected_papers: list[dict], date: str | None = None) -> list[dict]:
    """
    Format selected papers as Slack Block Kit blocks.
    Returns a list of blocks ready to POST to Slack.
    """
    date = date or datetime.now().strftime("%B %d, %Y")
    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"📚 GRIP Daily Digest — {date}"}
    })
    blocks.append({"type": "divider"})

    for i, paper in enumerate(selected_papers, 1):
        # Paper title as link
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{i}. <{paper['url']}|{paper['title']}>*\n"
                    f"_{paper.get('relevance_reason', '')}_\n\n"
                    f"{paper.get('summary', '')}"
                )
            }
        })

        # Relevance score badge
        score = paper.get("relevance_score", "?")
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Relevance score: *{score}/10* · React 👍 or 👎 to give feedback"}
            ]
        })
        blocks.append({"type": "divider"})

    # Footer
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": "GRIP · Your reactions help improve future selections"}
        ]
    })

    return blocks
