from typing import List
import os
import instructor
import asyncio
import time

from .models import (
    BatchExtraction,
    PostAnalysis,
    EntityResolutionResult,
)
from .prompts import TRIPLET_EXTRACTION_PROMPT, ENTITY_RESOLUTION_PROMPT
from .text_processing import format_posts_for_llm, format_entity_names_for_resolution


def get_llm_triplets(posts: List[dict]) -> BatchExtraction:
    """
    Given a list of post dicts {'id': str, 'text': str, 'url': str}, 
    extracts business triplets using LLM.
    """
    if not posts:
        return BatchExtraction(results=[])

    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("TRIPLET_EXTRACTOR_MODEL", "openrouter/google/gemini-2.0-flash-001")

    formatted_posts = format_posts_for_llm(posts)

    try:
        mode = instructor.Mode.OPENROUTER_STRUCTURED_OUTPUTS
        client = instructor.from_provider(model, api_key=api_key, mode=mode)
        
        start_llm = time.time()
        print(f"Sending batch of {len(posts)} posts to LLM for triplet extraction...")
        batch_results = client.create(
            response_model=BatchExtraction,
            messages=[
                {"role": "system", "content": TRIPLET_EXTRACTION_PROMPT},
                {"role": "user", "content": f"Analyze these posts:\n\n{formatted_posts}"}
            ],
            max_retries=2,
            max_tokens=16000
        )
        end_llm = time.time()
        print(f"Time for LLM extraction of batch with {len(posts)} posts: {end_llm - start_llm:.2f} seconds")
        return batch_results

    except Exception as exc:
        end_llm = time.time()
        print(f"Time until LLM extraction failure: {end_llm - start_llm:.2f} seconds")
        print(f"Failed to extract triplets: {exc}")
        return BatchExtraction(results=[PostAnalysis(post_id=p['id'], has_business_info=False, justification="Error") for p in posts])


async def get_llm_triplets_async(posts: list[dict]) -> BatchExtraction:
    """Async wrapper for get_llm_triplets."""
    return await asyncio.to_thread(get_llm_triplets, posts)


def resolve_entity_names(canonical_names: List[str]) -> dict[str, str]:
    """
    Given a list of canonical names, uses LLM to group entities that refer to the same 
    real-world entity and returns a mapping from each variant to its master name.
    
    Args:
        canonical_names: List of canonical entity names to resolve.
        
    Returns:
        A dictionary mapping each input name to its resolved master name.
    """
    if not canonical_names:
        return {}

    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("TRIPLET_EXTRACTOR_MODEL", "openrouter/google/gemini-2.0-flash-001")

    user_prompt = format_entity_names_for_resolution(canonical_names)

    try:
        mode = instructor.Mode.OPENROUTER_STRUCTURED_OUTPUTS
        client = instructor.from_provider(model, api_key=api_key, mode=mode)
        
        start_llm = time.time()
        print(f"Sending {len(canonical_names)} entity names to LLM for resolution...")
        
        resolution_result = client.create(
            response_model=EntityResolutionResult,
            messages=[
                {"role": "system", "content": ENTITY_RESOLUTION_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_retries=2,
            max_tokens=8000
        )
        
        end_llm = time.time()
        print(f"Time for entity resolution: {end_llm - start_llm:.2f} seconds")
        
        # Build mapping from variant to master name
        name_mapping: dict[str, str] = {}
        for group in resolution_result.groups:
            for variant in group.variants:
                name_mapping[variant] = group.master_name
            name_mapping[group.master_name] = group.master_name
        
        # For any names not in a group, map to themselves
        for name in canonical_names:
            if name not in name_mapping:
                name_mapping[name] = name
        
        print(f"Resolved {len(canonical_names)} names into {len(resolution_result.groups)} groups")
        return name_mapping

    except Exception as exc:
        print(f"Failed to resolve entity names: {exc}")
        return {name: name for name in canonical_names}


async def resolve_entity_names_async(canonical_names: List[str]) -> dict[str, str]:
    """Async wrapper for resolve_entity_names."""
    return await asyncio.to_thread(resolve_entity_names, canonical_names)
