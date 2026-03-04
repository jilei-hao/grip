"""
GRIP — Search Term Refiner

Reads the latest member_prefs_*.yml and current GRIP_SEARCH_TERMS,
calls Claude to suggest optimized search terms, and optionally writes
the result back to the .env file.

Usage:
    grip --refine-search           # suggest + update .env
    grip --refine-search --dry-run # print suggestions only
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import anthropic
import yaml

from grip.config import Settings, load_settings
from grip.profile.synthesizer import _find_latest_prefs, _format_member_responses
from grip.scorer.prompts import SEARCH_TERM_REFINEMENT_PROMPT


def refine_search_terms(settings: Settings | None = None, dry_run: bool = False) -> bool:
    """
    Suggest optimized GRIP_SEARCH_TERMS based on member_prefs_*.yml using Claude.

    - dry_run=True  → print suggestions only, do not modify .env
    - dry_run=False → print suggestions and update GRIP_SEARCH_TERMS in .env

    Returns True if terms were (or would be) produced successfully.
    """
    cfg = settings or load_settings()

    # 1. Load member preferences
    prefs_file = _find_latest_prefs(cfg.data_dir)
    if prefs_file is None:
        print(
            f"[refine-search] No member_prefs_*.yml found in {cfg.data_dir}.\n"
            "  Copy member_prefs_example.yml to member_prefs_YYYYMMDD.yml and fill it in."
        )
        return False

    print(f"[refine-search] Using preferences from: {prefs_file.name}")
    raw = yaml.safe_load(prefs_file.read_text(encoding="utf-8"))
    members = raw.get("members", []) if isinstance(raw, dict) else []
    if not members:
        print("[refine-search] No members found in the YAML file.")
        return False

    member_text = _format_member_responses(members)

    # 2. Gather current search terms for context
    current_terms_list = cfg.search_terms
    current_terms_str = ", ".join(current_terms_list) if current_terms_list else "(none set)"

    # 3. Build prompt and call Claude
    prompt = SEARCH_TERM_REFINEMENT_PROMPT.format(
        current_terms=current_terms_str,
        member_responses=member_text,
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    print(f"[refine-search] Calling Claude ({cfg.profile_update_model}) to refine search terms…")
    message = client.messages.create(
        model=cfg.profile_update_model,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_response = message.content[0].text.strip()  # type: ignore[union-attr]

    # Strip markdown fences if present
    if raw_response.startswith("```"):
        raw_response = raw_response.split("```", 2)[1]
        if raw_response.startswith("json"):
            raw_response = raw_response[4:]
        raw_response = raw_response.strip()

    result = json.loads(raw_response)
    suggested_terms: list[str] = result.get("search_terms", [])
    reasoning: str = result.get("reasoning", "")

    if not suggested_terms:
        print("[refine-search] Claude returned no terms. Aborting.")
        return False

    # 4. Display results
    print("\n── Suggested GRIP_SEARCH_TERMS ─────────────────────────────────────")
    for t in suggested_terms:
        print(f"  • {t}")
    print(f"\nReasoning: {reasoning}")
    terms_value = ",".join(suggested_terms)
    print(f"\nGRIP_SEARCH_TERMS={terms_value}")
    print("────────────────────────────────────────────────────────────────────\n")

    if dry_run:
        print("[refine-search] Dry run — .env not modified.")
        return True

    # 5. Update .env
    env_path = _find_env_file()
    if env_path is None:
        print(
            "[refine-search] No .env file found. Add the following line manually:\n"
            f"  GRIP_SEARCH_TERMS={terms_value}"
        )
        return True

    _update_env_file(env_path, terms_value)
    print(f"[refine-search] Updated GRIP_SEARCH_TERMS in {env_path}")
    return True


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_env_file() -> Path | None:
    """Search for a .env file: cwd first, then up to three parent levels."""
    cwd = Path.cwd()
    candidates = [cwd / ".env"] + [cwd.parents[i] / ".env" for i in range(3)]
    for p in candidates:
        if p.exists():
            return p
    return None


def _update_env_file(env_path: Path, new_value: str) -> None:
    """
    Replace the GRIP_SEARCH_TERMS=... line in *env_path*.
    If the key is absent, append it after a comment block at the end.
    """
    text = env_path.read_text(encoding="utf-8")
    pattern = re.compile(r"^GRIP_SEARCH_TERMS=.*$", re.MULTILINE)
    replacement = f"GRIP_SEARCH_TERMS={new_value}"

    if pattern.search(text):
        updated = pattern.sub(replacement, text)
    else:
        updated = text.rstrip("\n") + f"\n{replacement}\n"

    env_path.write_text(updated, encoding="utf-8")
