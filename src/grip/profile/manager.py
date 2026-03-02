"""
GRIP — Profile Manager
Handles reading, writing, and versioning of the group interest profile.

The profile is a plain text document — human readable and directly editable.
Versioning saves dated copies on every write so you can always roll back.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from grip.config import Settings, load_settings


class ProfileManager:

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()

    @property
    def profile_path(self) -> Path:
        return self._settings.profile_path

    @property
    def versions_dir(self) -> Path:
        return self._settings.profile_versions_dir

    def load(self) -> str:
        """Load the current interest profile."""
        if not self.profile_path.exists():
            raise FileNotFoundError(
                f"No interest profile found at {self.profile_path}.\n"
                "Run `grip init` to create a starter profile, or copy one manually."
            )
        return self.profile_path.read_text(encoding="utf-8").strip()

    def save(self, new_profile: str, reason: str = "manual update") -> None:
        """
        Save updated profile, archiving the previous version first.
        Always archives before overwriting — easy to roll back.
        """
        self._archive_current()
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        self.profile_path.write_text(new_profile, encoding="utf-8")
        print(f"[profile] Updated ({reason}). Previous version archived.")

    def _archive_current(self) -> None:
        """Copy current profile to timestamped archive."""
        if not self.profile_path.exists():
            return
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy(self.profile_path, self.versions_dir / f"profile_{timestamp}.txt")

    def list_versions(self) -> list[Path]:
        """Return all archived versions, newest first."""
        if not self.versions_dir.exists():
            return []
        return sorted(self.versions_dir.glob("profile_*.txt"), reverse=True)

    def rollback(self, version_path: Path) -> None:
        """Restore a specific archived version."""
        self._archive_current()
        shutil.copy(version_path, self.profile_path)
        print(f"[profile] Rolled back to {version_path.name}")
