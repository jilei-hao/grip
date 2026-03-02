# GRIP — Group Research Intelligence Pipeline

> Daily paper digest delivered to Slack, curated by Claude, improving from your team's 👍/👎 reactions.

## Install

```bash
pip install grip-digest
```

Or for development (editable install):

```bash
git clone https://github.com/your-org/grip
cd grip
pip install -e ".[dev]"
```

## Setup

**1. Configure secrets**
```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and GRIP_SLACK_WEBHOOK
```

**2. Initialize your interest profile**
```bash
grip init
# Creates interest_profile.txt in current directory
# Edit it, then set GRIP_DATA_DIR to this directory
```

**3. Test without posting**
```bash
grip --dry-run
```

**4. Run for real**
```bash
grip
```

## CLI Reference

| Command | Description |
|---|---|
| `grip` | Run daily digest and post to Slack |
| `grip --dry-run` | Fetch + score, print results, skip Slack |
| `grip --update-profile` | Update profile from recent 👍/👎 feedback |
| `grip init` | Copy starter `interest_profile.txt` to current dir |
| `grip version` | Print installed version |

## Project Structure

```
src/grip/
├── __init__.py
├── cli.py                   ← entry point (grip command)
├── pipeline.py              ← orchestrates fetch→score→post
├── config.py                ← Settings dataclass + env loading
├── fetchers/
│   ├── base.py              ← Paper dataclass + BaseFetcher ABC
│   ├── arxiv.py             ← arXiv API (active)
│   ├── semantic_scholar.py  ← stub (implement when ready)
│   └── rss.py               ← stub (implement when ready)
├── scorer/
│   ├── claude_scorer.py     ← Claude API scoring
│   └── prompts.py           ← all prompts (tune here)
├── notifier/
│   ├── slack.py             ← Slack webhook poster
│   └── formatter.py         ← Block Kit formatting
├── feedback/
│   ├── collector.py         ← logs 👍/👎 from Slack Events API
│   └── updater.py           ← weekly profile update from feedback
├── profile/
│   └── manager.py           ← read/write/version interest profile
├── utils/
│   └── dedup.py             ← deduplication across sources
├── tests/
│   ├── test_fetchers.py
│   ├── test_config.py
│   └── test_feedback.py
└── data/
    ├── interest_profile.txt          ← bundled starter profile
    ├── feedback_log/                 ← YYYY-MM-DD.jsonl per day
    └── profile_versions/            ← auto-archived history
```

## Adding a New Source

1. Create `src/grip/fetchers/your_source.py`:
```python
from grip.fetchers.base import BaseFetcher, Paper

class YourFetcher(BaseFetcher):
    source_name = "Your Source"

    def fetch_papers(self) -> list[Paper]:
        # fetch, parse, return list[Paper]
        ...
```

2. Add to `pipeline.py` (one line):
```python
papers += YourFetcher(...).fetch_papers()
```

3. If it needs extra dependencies, add an optional group in `pyproject.toml`:
```toml
[project.optional-dependencies]
your-source = ["some-package>=1.0"]
```

Then: `pip install "grip-digest[your-source]"`

## Tuning

| What to change | Where |
|---|---|
| Which papers get selected | Edit `data/interest_profile.txt` |
| Scoring behaviour / summary format | Edit `scorer/prompts.py` |
| Number of papers per digest | `GRIP_TOP_N` env var |
| How often profile updates | `GRIP_MIN_FEEDBACK`, `GRIP_FEEDBACK_DAYS` |

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```
