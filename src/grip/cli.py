"""
GRIP — CLI Entry Point

Registered as console_scripts in pyproject.toml, so after `pip install`:

    grip                        # run daily digest
    grip --dry-run              # fetch + score, print results, skip Slack
    grip --update-profile       # synthesize profile from member_prefs, refine
                                #   search terms, then apply feedback reactions
    grip --update-profile --dry-run  # preview each step without saving
    grip init                   # copy starter profile to current directory
    grip version                # print version

"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="grip",
        description="GRIP — Group Research Intelligence Pipeline",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and score papers without posting to Slack; or preview synthesize-profile without saving.",
    )
    parser.add_argument(
        "--update-profile",
        action="store_true",
        help=(
            "Full profile update: synthesize interest_profile.txt from member_prefs_*.yml, "
            "refine search terms, then apply feedback reactions."
        ),
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["init", "version"],
        help=(
            "init: copy starter profile to ./interest_profile.txt | "
            "version: print version"
        ),
    )
    args = parser.parse_args()

    # Load .env if present (no-op if not)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv is a dep, but don't crash if somehow missing

    if args.command == "version":
        import grip
        print(f"grip-digest {grip.__version__}")
        return

    if args.command == "init":
        _init_profile()
        return

    if args.update_profile:
        from grip.profile.synthesizer import synthesize_profile
        from grip.profile.search_refiner import refine_search_terms
        from grip.pipeline import run_profile_update

        print("── Step 1/3: Synthesize profile from member_prefs ──")
        synthesize_profile(dry_run=args.dry_run)

        print("── Step 2/3: Refine search terms ──")
        refine_search_terms(dry_run=args.dry_run)

        print("── Step 3/3: Apply feedback reactions ──")
        run_profile_update()

        print("── Profile update complete ──")
        return

    from grip.pipeline import run_digest
    selected = run_digest(dry_run=args.dry_run)
    sys.exit(0 if selected else 1)


def update_profile() -> None:
    """Secondary entry point: grip-update-profile"""
    import argparse as _ap
    p = _ap.ArgumentParser(prog="grip-update-profile")
    p.add_argument("--dry-run", action="store_true", help="Preview each step without saving.")
    args = p.parse_args()
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from grip.profile.synthesizer import synthesize_profile
    from grip.profile.search_refiner import refine_search_terms
    from grip.pipeline import run_profile_update

    print("── Step 1/3: Synthesize profile from member_prefs ──")
    synthesize_profile(dry_run=args.dry_run)

    print("── Step 2/3: Refine search terms ──")
    refine_search_terms(dry_run=args.dry_run)

    print("── Step 3/3: Apply feedback reactions ──")
    run_profile_update()

    print("── Profile update complete ──")


def synthesize_profile_entry() -> None:
    """Secondary entry point: grip-synthesize-profile"""
    import argparse as _ap
    p = _ap.ArgumentParser(prog="grip-synthesize-profile")
    p.add_argument("--dry-run", action="store_true", help="Print result without saving.")
    args = p.parse_args()
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from grip.profile.synthesizer import synthesize_profile
    ok = synthesize_profile(dry_run=args.dry_run)
    sys.exit(0 if ok else 1)


def _init_profile() -> None:
    """Copy the bundled starter profile to the current directory."""
    import grip
    src = grip.DEFAULT_PROFILE_PATH
    dest = Path.cwd() / "interest_profile.txt"

    if dest.exists():
        print(f"[init] {dest} already exists. Not overwriting.")
        print("[init] Delete it first if you want a fresh copy.")
        sys.exit(1)

    shutil.copy(src, dest)
    print(f"[init] Starter profile written to {dest}")
    print("[init] Set GRIP_DATA_DIR to the directory containing it, then run `grip --dry-run`.")
