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
# Fill in ANTHROPIC_API_KEY, GRIP_SLACK_BOT_TOKEN, and GRIP_SLACK_CHANNEL_ID
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
| `grip` | Update profile, then run daily digest and post to Slack |
| `grip --dry-run` | Fetch + score + preview profile update steps, skip Slack |
| `grip init` | Copy starter `interest_profile.txt` to current dir |
| `grip version` | Print installed version |

## How the Feedback Loop Works

Each daily digest is posted as a **threaded Slack message**: a compact header lists
the paper titles, and each paper gets its own thread reply with a full summary.
A final reply explains why those papers were selected (profile excerpt + scorer notes).

Team members react 👍 or 👎 on individual thread replies, or leave text comments.
Each time `grip` runs, it automatically polls those reactions and comments via
the Slack Web API, then calls Claude to revise the group interest profile
accordingly. No server or webhook endpoint is required — feedback collection is
fully pull-based.

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
│   ├── medrxiv_biorxiv.py   ← bioRxiv / medRxiv API (active)
│   ├── pubmed.py            ← PubMed E-utilities (active)
│   ├── semantic_scholar.py  ← stub (implement when ready)
│   └── rss.py               ← stub (implement when ready)
├── scorer/
│   ├── claude_scorer.py     ← Claude API scoring; returns (papers, selection_notes)
│   └── prompts.py           ← all prompts (tune here)
├── notifier/
│   ├── slack.py             ← threaded bot poster + webhook fallback
│   └── formatter.py         ← Block Kit formatting (header, paper, explanation blocks)
├── feedback/
│   ├── collector.py         ← polls 👍/👎 reactions + thread comments from Slack
│   ├── digest_registry.py   ← maps Slack message timestamps → paper metadata
│   └── updater.py           ← profile update from accumulated feedback
├── profile/
│   ├── manager.py           ← read/write/version interest profile
│   ├── synthesizer.py       ← synthesize profile from member_prefs_*.yml
│   └── search_refiner.py    ← refine search terms from profile
├── utils/
│   └── dedup.py             ← deduplication across sources
├── tests/
│   ├── test_fetchers.py
│   ├── test_config.py
│   └── test_feedback.py
└── data/
    ├── interest_profile.example.txt  ← bundled starter profile
    ├── member_prefs_example.yml      ← starter member preferences template
    ├── feedback_log/                 ← YYYY-MM-DD.jsonl per day
    ├── digest_log/                   ← YYYY-MM-DD.json per day (ts → paper map)
    └── profile_versions/            ← auto-archived history
```

## Docs

| Guide | Description |
|---|---|
| [docs/slack-bot-setup.md](docs/slack-bot-setup.md) | Create the Slack app, set OAuth scopes, find Channel ID |
| [docs/paper-sources.md](docs/paper-sources.md) | arXiv, bioRxiv, medRxiv, PubMed — setup and tuning |

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
