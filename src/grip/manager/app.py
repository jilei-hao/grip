"""
GRIP Manager — Flask web application.

Serves a UI for members to read and edit member_prefs_example.yml.
Each save writes both a timestamped archive copy and updates the canonical file.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import yaml
from flask import Flask, abort, jsonify, render_template, request


# ── YAML helpers ──────────────────────────────────────────────────────────────

class _LiteralDumper(yaml.Dumper):
    """Dumps multi-line strings as YAML block scalars (|)."""


def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_LiteralDumper.add_representer(str, _str_representer)


def _load_members(prefs_path: Path) -> list[dict]:
    if not prefs_path.exists():
        return []
    raw = yaml.safe_load(prefs_path.read_text(encoding="utf-8"))
    members = (raw or {}).get("members") or []
    return [m for m in members if isinstance(m, dict)]


def _dump_yaml(members: list[dict], timestamp: str) -> str:
    header = (
        "# GRIP Member Preference Responses\n"
        f"# Last updated: {timestamp}\n"
        "# ──────────────────────────────────────────────────────────────────────\n"
        "# Edit via:  grip manager  (web UI)  or manually.\n"
        "# Run `grip synthesize-profile` after editing to rebuild interest_profile.txt.\n"
        "# ──────────────────────────────────────────────────────────────────────\n\n"
    )
    buf = io.StringIO()
    yaml.dump(
        {"members": members},
        buf,
        Dumper=_LiteralDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    return header + buf.getvalue()


# ── Flask application factory ─────────────────────────────────────────────────

def create_app(data_dir: Path | None = None) -> Flask:
    if data_dir is None:
        from grip.config import load_settings
        data_dir = load_settings().data_dir

    prefs_path = data_dir / "member_prefs_example.yml"

    app = Flask(__name__)

    @app.route("/")
    def index():  # type: ignore[return]
        return render_template("index.html")

    @app.route("/api/members", methods=["GET"])
    def get_members():  # type: ignore[return]
        return jsonify({"members": _load_members(prefs_path)})

    @app.route("/api/update", methods=["POST"])
    def update_members():  # type: ignore[return]
        payload = request.get_json(silent=True)
        if not payload or "members" not in payload:
            abort(400, description="Request body must contain 'members'.")

        members: list[dict] = payload["members"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content = _dump_yaml(members, timestamp)

        # Archive copy (timestamped)
        archive_path = data_dir / f"member_prefs_{timestamp}.yml"
        archive_path.write_text(content, encoding="utf-8")

        # Update canonical file
        prefs_path.write_text(content, encoding="utf-8")

        return jsonify({"status": "ok", "saved_as": archive_path.name})

    return app


def run(host: str = "127.0.0.1", port: int = 5000, debug: bool = False,
        data_dir: Path | None = None) -> None:
    app = create_app(data_dir=data_dir)
    print(f"[grip-manager] Starting on http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug)
