"""
GRIP — Claude Scorer
Sends fetched papers to Claude for relevance scoring and summarization.
"""

from __future__ import annotations

import json
import anthropic

from grip.config import Settings, get_httpx_client, load_settings
from grip.fetchers.base import Paper
from grip.scorer.prompts import SCORING_SYSTEM_PROMPT


class ClaudeScorer:

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()
        self._client = anthropic.Anthropic(
            api_key=self._settings.anthropic_api_key,
            http_client=get_httpx_client(),
        )

    def score(self, papers: list[Paper], interest_profile: str) -> list[dict]:
        """
        Score papers against the interest profile.
        Returns selected papers with summaries, ranked by relevance.
        """
        papers_text = "\n\n---\n\n".join(p.to_prompt_str() for p in papers)
        top_n = self._settings.top_n_papers

        system_prompt = SCORING_SYSTEM_PROMPT.format(
            interest_profile=interest_profile,
            top_n=top_n,
        )

        print(f"[scorer] Scoring {len(papers)} papers with {self._settings.scoring_model}...")

        response = self._client.messages.create(
            model=self._settings.scoring_model,
            max_tokens=2000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"Here are today's papers:\n\n{papers_text}"}
            ],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if the model wrapped the JSON
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        result = json.loads(raw)
        selected = result.get("selected", [])
        notes = result.get("selection_notes", "")
        print(f"[scorer] Selected {len(selected)} papers. Notes: {notes}")
        return selected
