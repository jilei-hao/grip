"""
GRIP — Profile Updater
Core of the learning loop: uses accumulated 👍/👎 feedback to update
the interest profile via Claude. Run weekly, not daily.
"""

from __future__ import annotations

import json
import anthropic

from grip.config import Settings, load_settings
from grip.feedback.collector import FeedbackCollector
from grip.profile.manager import ProfileManager
from grip.scorer.prompts import PROFILE_UPDATE_PROMPT


class ProfileUpdater:

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()
        self._collector = FeedbackCollector(self._settings)
        self._profile = ProfileManager(self._settings)
        self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

    def run_update(self) -> bool:
        """
        Pull recent feedback and update the profile if enough signal exists.
        Returns True if profile was updated, False if skipped (too little feedback).
        """
        feedback = self._collector.load_recent()
        min_count = self._settings.min_feedback_to_update

        if len(feedback) < min_count:
            print(
                f"[updater] {len(feedback)} reactions found, need {min_count}. Skipping."
            )
            return False

        positive = [f for f in feedback if f["sentiment"] == "positive"]
        negative = [f for f in feedback if f["sentiment"] == "negative"]

        print(
            f"[updater] Updating profile from {len(feedback)} reactions "
            f"({len(positive)} 👍, {len(negative)} 👎)..."
        )

        prompt = PROFILE_UPDATE_PROMPT.format(
            current_profile=self._profile.load(),
            thumbs_up_papers=json.dumps(positive, indent=2),
            thumbs_down_papers=json.dumps(negative, indent=2),
        )

        response = self._client.messages.create(
            model=self._settings.profile_update_model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        new_profile = response.content[0].text.strip()
        self._profile.save(
            new_profile,
            reason=f"feedback update ({len(feedback)} reactions)"
        )
        return True
