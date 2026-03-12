"""
GRIP — Feedback Server
Receives Slack Events API webhooks for reaction_added / reaction_removed events
and logs them via FeedbackCollector.

Install deps:  pip install "grip[feedback-server]"
Run directly:  grip-feedback-server
Run in prod:   see scripts/setup_feedback_service.sh

Slack Events API setup:
  1. Go to https://api.slack.com/apps → Your App → Event Subscriptions
  2. Enable Events and set the Request URL to:
       https://<your-host>/slack/events
  3. Subscribe to bot events: reaction_added, reaction_removed
  4. Copy the Signing Secret (Basic Information → App Credentials) to
     GRIP_SLACK_SIGNING_SECRET in your .env
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time

from grip.config import load_settings
from grip.feedback.collector import FeedbackCollector

try:
    from flask import Flask, Request, abort, jsonify, request
except ImportError as exc:
    raise ImportError(
        "Flask is required for the feedback server.\n"
        "Install it with:  pip install 'grip[feedback-server]'"
    ) from exc

app = Flask(__name__)
_settings = load_settings()
_collector = FeedbackCollector(_settings)


# ── Slack signature verification ──────────────────────────────────────────────

def _verify_slack_signature(req: Request) -> bool:
    """
    Verify the X-Slack-Signature header using HMAC-SHA256.
    Rejects requests older than 5 minutes to prevent replay attacks.
    Returns True if the signature is valid, False otherwise.
    """
    signing_secret = _settings.slack_signing_secret
    if not signing_secret:
        # If no signing secret is configured, skip verification (not recommended for production)
        return True

    timestamp = req.headers.get("X-Slack-Request-Timestamp", "")
    slack_signature = req.headers.get("X-Slack-Signature", "")

    # Reject stale requests (> 5 minutes old)
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except (ValueError, TypeError):
        return False

    sig_basestring = f"v0:{timestamp}:{req.get_data(as_text=True)}"
    my_signature = "v0=" + hmac.new(
        signing_secret.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(my_signature, slack_signature)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health() -> tuple:
    """Simple health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.route("/slack/events", methods=["POST"])
def slack_events() -> tuple:
    """
    Handle Slack Events API callbacks.

    Supports:
      - url_verification  → echo the challenge (required by Slack during setup)
      - reaction_added    → log positive/negative feedback
      - reaction_removed  → log removal
    """
    if not _verify_slack_signature(request):
        abort(403)

    payload = request.get_json(force=True, silent=True) or {}
    event_type = payload.get("type")

    # ── URL verification handshake ─────────────────────────────────────────
    if event_type == "url_verification":
        return jsonify({"challenge": payload.get("challenge")}), 200

    # ── Reaction events ────────────────────────────────────────────────────
    if event_type == "event_callback":
        event = payload.get("event", {})
        if event.get("type") in ("reaction_added", "reaction_removed"):
            _collector.handle_reaction(event)

    # Acknowledge all other events with 200 (Slack requires a fast response)
    return jsonify({"ok": True}), 200


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """Console script entry point: grip-feedback-server"""
    host = os.environ.get("GRIP_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("GRIP_SERVER_PORT", "5000"))
    debug = os.environ.get("GRIP_SERVER_DEBUG", "false").lower() in ("true", "1", "yes")

    print(f"[server] Starting GRIP feedback server on {host}:{port}")
    print(f"[server] POST your Slack Events to: http://{host}:{port}/slack/events")
    if not _settings.slack_signing_secret:
        print("[server] WARNING: GRIP_SLACK_SIGNING_SECRET is not set — request signatures will not be verified!")

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
