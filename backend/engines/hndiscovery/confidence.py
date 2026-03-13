"""Query confidence scoring for Hacker News discovery."""

from pydantic import BaseModel, Field

from ..llm_utils import call_llm_async


QUERY_CONFIDENCE_PROMPT = """
You are a Hacker News coverage analyst. Given a search query, estimate the likelihood (0-100) that this query will return meaningful stories and comments on Hacker News.

### SCORING GUIDELINES:
- **80-100**: Major tech companies, trending tech topics, well-known founders/CEOs (e.g., "OpenAI", "Google", "Elon Musk", "React", "Rust programming").
- **50-79**: Moderately known companies, niche but active tech topics, industry-specific terms (e.g., "Supabase", "Zig language", "RISC-V").
- **20-49**: Obscure companies, very niche topics, non-tech subjects with occasional HN presence (e.g., small local startups, specialized academic topics).
- **0-19**: Completely unrelated to HN audience, nonsensical queries, very obscure entities with near-zero chance of HN coverage.

### RULES:
1. Consider that Hacker News primarily covers technology, startups, programming, science, and business.
2. Well-known companies and people in tech will almost always have coverage.
3. Be realistic — do not inflate scores for obscure queries.

Return ONLY a valid JSON object matching the provided schema.
"""


class QueryConfidence(BaseModel):
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score (0-100) that this query will yield meaningful Hacker News results.",
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of why this score was assigned.",
    )


async def evaluate_query_confidence(query: str) -> QueryConfidence:
    """
    Use an LLM to score how likely *query* is to produce useful HN results.

    Returns a :class:`QueryConfidence` with ``score`` (0-100) and ``reasoning``.
    """
    return await call_llm_async(
        response_model=QueryConfidence,
        system_prompt=QUERY_CONFIDENCE_PROMPT,
        user_prompt=f"Query: {query}",
        max_tokens=1024,
    )
