# GRIP Paper Sources

GRIP fetches preprints and articles from multiple sources every run, deduplicates
them by DOI (or title as fallback), scores them with Claude, and posts the top
results to Slack.

The active sources are:

| Source | Fetcher class | API key needed? |
|---|---|---|
| **arXiv** | `ArxivFetcher` | No |
| **bioRxiv** | `BioRxivFetcher(server="biorxiv")` | No |
| **medRxiv** | `BioRxivFetcher(server="medrxiv")` | No |
| **PubMed** | `PubMedFetcher` | Optional (increases rate limit) |

---

## arXiv

- **Coverage:** Computer science, physics, mathematics, quantitative biology, and more.
- **API:** Public Atom feed — no registration required.
- **How GRIP queries it:** Keyword search across title and abstract fields
  using your `GRIP_SEARCH_TERMS`.
- **Rate limit:** Polite use; no key required.

No setup needed.

---

## bioRxiv & medRxiv

- **Coverage:**
  - bioRxiv — life sciences preprints (genomics, neuroscience, bioinformatics, …)
  - medRxiv — clinical / health sciences preprints
- **API:** Public bioRxiv content API (`https://api.biorxiv.org/`) — no registration.
- **How GRIP queries it:** The API does not support keyword search; GRIP fetches
  all preprints posted in the lookback window and filters **client-side** against
  `GRIP_SEARCH_TERMS` in title + abstract.
- **Optional category filter:** You can narrow results to specific subject areas
  by passing a `categories` list to `BioRxivFetcher`. Example subjects for
  bioRxiv: `neuroscience`, `genomics`, `bioinformatics`. For medRxiv:
  `neurology`, `radiology`, `oncology`.

No setup needed. To add category filtering, edit the fetcher calls in
[`src/grip/pipeline.py`](../src/grip/pipeline.py):

```python
BioRxivFetcher(
    search_terms=s.search_terms,
    server="biorxiv",
    categories=["neuroscience", "bioinformatics"],   # ← add this
    days_lookback=s.days_lookback,
    max_results=s.max_fetch_per_source,
).fetch_papers()
```

---

## PubMed

- **Coverage:** Biomedical and life-science literature indexed by NCBI, including
  peer-reviewed journal articles.
- **API:** NCBI E-utilities (`esearch` + `efetch`) — free, no key required for
  light usage.
- **How GRIP queries it:** Title/Abstract field search using `GRIP_SEARCH_TERMS`,
  filtered to the lookback date range via the `reldate` parameter.
- **Rate limit:**
  - **Without API key:** 3 requests / second
  - **With API key:** 10 requests / second

### Getting an NCBI API Key (recommended)

1. Create a free NCBI account at <https://www.ncbi.nlm.nih.gov/account/>.
2. After logging in, go to **Account Settings** → **API Key Management**.
3. Click **Create an API Key**.
4. Copy the generated key.

### Adding the key to GRIP

Open `.env` and uncomment + fill in:

```dotenv
NCBI_API_KEY=your_ncbi_api_key_here
```

GRIP picks this up automatically via the `Settings.ncbi_api_key` property — no
other changes needed.

---

## Tuning the pipeline

All source-related knobs live in `.env`:

| Variable | Default | Effect |
|---|---|---|
| `GRIP_SEARCH_TERMS` | `machine learning,deep learning` | Comma-separated keywords searched in every source |
| `GRIP_DAYS_LOOKBACK` | `1` | How many calendar days back each source queries |
| `GRIP_MAX_FETCH` | `30` | Maximum papers fetched **per source** before deduplication |
| `NCBI_API_KEY` | _(unset)_ | Optional NCBI key; raises PubMed rate limit |

### Adding or removing sources

Sources are wired together in [`src/grip/pipeline.py`](../src/grip/pipeline.py)
under the `# 2. Fetch from all active sources` comment. To disable a source,
delete or comment out its block. To add a custom RSS feed or a new fetcher,
append another `papers +=` call following the same pattern.

### Deduplication

After all sources are fetched, `deduplicate()` in
[`src/grip/utils/dedup.py`](../src/grip/utils/dedup.py) collapses identical
papers using DOI as the primary key (title-normalised string as fallback). The
same preprint posted to both bioRxiv and PubMed, for example, will appear only
once if both carry the same DOI.
