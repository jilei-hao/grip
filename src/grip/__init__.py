"""
GRIP — Group Research Intelligence Pipeline

Daily paper digest delivered to Slack, curated by Claude,
learning from your group's 👍/👎 feedback.

Quickstart:
    pip install grip-digest
    cp $(python -c "import grip; print(grip.DEFAULT_PROFILE_PATH)") ./interest_profile.txt
    grip --dry-run
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("grip-digest")
except PackageNotFoundError:
    __version__ = "dev"

# Expose the default data path so users can bootstrap their profile
from pathlib import Path
DEFAULT_PROFILE_PATH = Path(__file__).parent / "data" / "interest_profile.txt"
