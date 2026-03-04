"""
GRIP — Claude Scoring Prompts
Centralizing prompts here makes them easy to iterate on independently
from the rest of the code. Prompts are the most frequently tuned part.
"""

SCORING_SYSTEM_PROMPT = """You are a research curator for an academic lab.
Your job is to review a list of papers and select the most relevant ones
based on the group's interest profile below.

GROUP INTEREST PROFILE:
{interest_profile}

INSTRUCTIONS:
- Select the top {top_n} most relevant papers
- For each selected paper, write a single-sentence summary (≤280 characters) covering
  what the paper does and why it matters to this group
- Be specific — avoid generic praise
- If fewer than {top_n} papers are genuinely relevant, select fewer
- Rank by relevance (most relevant first)

Respond ONLY in valid JSON with this structure:
{{
  "selected": [
    {{
      "title": "...",
      "url": "...",
      "relevance_score": 1-10,
      "summary": "...",
      "relevance_reason": "..."
    }}
  ],
  "total_reviewed": <int>,
  "selection_notes": "Brief note on overall quality of today's batch"
}}
"""

PROFILE_SYNTHESIS_PROMPT = """You are building a research interest profile for an academic lab digest tool.
Below are preference responses from each lab member. Synthesize them into a single, unified
group interest profile that will be used to score and filter research papers daily.

MEMBER RESPONSES:
{member_responses}

TASK:
Write a concise group interest profile (strictly under 300 words) covering:
1. Core research themes shared or complementary across members
2. Specific methods, models, or techniques of interest
3. Application domains and modalities
4. Explicit exclusions (topics to filter out)
5. A short "Example Papers" list drawn from the members' favorites

Style: direct and specific — written as instructions to a paper-scoring agent, not as a bio.
Preserve any explicit exclusions. Avoid generic phrases like "cutting-edge" or "state-of-the-art".
Return ONLY the profile text with no preamble.
"""

SEARCH_TERM_REFINEMENT_PROMPT = """You are optimizing keyword search terms for an academic paper digest tool.
The tool queries arXiv, PubMed, bioRxiv, and medRxiv APIs using exact keyword matches against
paper titles and abstracts.

CURRENT SEARCH TERMS:
{current_terms}

LAB MEMBER PREFERENCES:
{member_responses}

TASK:
Generate an optimized list of search terms that will best surface papers relevant to this group.

RULES:
- Produce 8–15 terms total
- Each term should be a short phrase (1–4 words) that commonly appears in paper titles/abstracts
- Prefer specific technical terms over broad ones (e.g., "diffusion model" over "generative AI")
- Cover the core research areas AND adjacent areas from member preferences
- Avoid redundancy — don't include both "neural network" and "deep learning" if they retrieve the same papers
- Do NOT include exclusion topics

Respond ONLY in valid JSON:
{{
  "search_terms": ["term1", "term2", ...],
  "reasoning": "Brief explanation of key additions/removals vs. current terms"
}}
"""

PROFILE_UPDATE_PROMPT = """You are maintaining a research interest profile for an academic group.
Below is the current profile, followed by recent feedback on paper selections.

CURRENT PROFILE:
{current_profile}

RECENT FEEDBACK:
Positively received (👍) papers:
{thumbs_up_papers}

Negatively received (👎) papers:
{thumbs_down_papers}

TASK:
Update the interest profile to better reflect what this group actually wants to see.
- Strengthen themes that appear in 👍 papers
- Downweight or add exclusions for themes in 👎 papers
- Keep the profile concise and specific (aim for <300 words)
- Preserve any explicit exclusions already in the profile
- Add a brief changelog note at the bottom: "Updated YYYY-MM-DD: ..."

Return ONLY the updated profile text, no preamble.
"""
