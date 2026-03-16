"""
GRIP — Profile Synthesizer

Reads the latest member_prefs_YYYYMMDD.yml from the data directory,
calls Claude to synthesize a <300-word group interest profile, and
saves it via ProfileManager.

Usage:
    grip synthesize-profile
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import anthropic
import yaml

from grip.config import Settings, get_httpx_client, load_settings
from grip.profile.manager import ProfileManager
from grip.scorer.prompts import PROFILE_SYNTHESIS_PROMPT


_PREFS_HASH_FILE = ".member_prefs_hash"


def _find_latest_prefs(data_dir: Path) -> Path | None:
    """Return the most recent member_prefs_*.yml file, or None if none exist."""
    candidates = sorted(data_dir.glob("member_prefs_*.yml"), reverse=True)
    # Skip the example template
    candidates = [p for p in candidates if p.name != "member_prefs_example.yml"]
    return candidates[0] if candidates else None


def _compute_prefs_hash(prefs_file: Path) -> str:
    """Return a hash string encoding both the filename and file content."""
    digest = hashlib.sha256(prefs_file.read_bytes()).hexdigest()
    return f"{prefs_file.name}:{digest}"


def prefs_changed(data_dir: Path) -> bool:
    """Return True if the latest member_prefs file differs from the last recorded hash."""
    prefs_file = _find_latest_prefs(data_dir)
    if prefs_file is None:
        return False
    hash_path = data_dir / _PREFS_HASH_FILE
    if hash_path.exists() and hash_path.read_text(encoding="utf-8").strip() == _compute_prefs_hash(prefs_file):
        return False
    return True


def save_prefs_hash(data_dir: Path) -> None:
    """Persist the hash of the current latest member_prefs file."""
    prefs_file = _find_latest_prefs(data_dir)
    if prefs_file is None:
        return
    (data_dir / _PREFS_HASH_FILE).write_text(_compute_prefs_hash(prefs_file), encoding="utf-8")


def _to_str(value: object) -> str:
    """Normalise a YAML field that may be a string, a list, or None."""
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(v) for v in value)
    return str(value)


def _format_member_responses(members: list[dict]) -> str:  # type: ignore[type-arg]
    """Render member YAML dicts into a readable text block for the prompt."""
    parts: list[str] = []
    for m in members:
        name = m.get("name", "Unknown")
        role = m.get("role", "")
        header = f"### {name}" + (f" ({role})" if role else "")
        lines = [header]

        if research := _to_str(m.get("research_areas")).strip():
            lines.append(f"Research areas:\n{research}")
        if adjacent := _to_str(m.get("adjacent_areas")).strip():
            lines.append(f"Adjacent areas of interest:\n{adjacent}")
        if papers := m.get("example_papers"):
            lines.append("Example papers they like:")
            for p in papers:
                lines.append(f"  - {p}")
        if excl := _to_str(m.get("exclusions")).strip():
            lines.append(f"Exclusions:\n{excl}")
        if notes := _to_str(m.get("notes")).strip():
            lines.append(f"Notes:\n{notes}")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def synthesize_profile(settings: Settings | None = None, dry_run: bool = False) -> bool:
    """
    Find the latest member_prefs_*.yml, synthesize via Claude, and save.

    Returns True if the profile was updated, False otherwise.
    """
    cfg = settings or load_settings()
    data_dir = cfg.data_dir

    prefs_file = _find_latest_prefs(data_dir)
    if prefs_file is None:
        print(
            f"[synthesizer] No member_prefs_*.yml found in {data_dir}.\n"
            "  Copy member_prefs_example.yml to member_prefs_YYYYMMDD.yml and fill it in."
        )
        return False

    print(f"[synthesizer] Using preferences from: {prefs_file.name}")

    raw = yaml.safe_load(prefs_file.read_text(encoding="utf-8"))
    members = raw.get("members", []) if isinstance(raw, dict) else []
    if not members:
        print("[synthesizer] No members found in the YAML file.")
        return False

    member_text = _format_member_responses(members)
    prompt = PROFILE_SYNTHESIS_PROMPT.format(member_responses=member_text)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key, http_client=get_httpx_client())
    print(f"[synthesizer] Calling Claude ({cfg.profile_update_model}) to synthesize profile…")
    message = client.messages.create(
        model=cfg.profile_update_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    new_profile = message.content[0].text.strip()  # type: ignore[union-attr]

    if dry_run:
        print("\n── Synthesized profile (dry-run, not saved) ──────────────────────")
        print(new_profile)
        print("──────────────────────────────────────────────────────────────────\n")
        return True

    manager = ProfileManager(cfg)
    manager.save(new_profile, reason=f"synthesized from {prefs_file.name}")
    print("[synthesizer] Profile saved.")
    return True
