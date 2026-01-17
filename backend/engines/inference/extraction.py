from typing import List
import asyncio
import time
import json

from .models import (
    PostAnalysis,
    ResolvedTriplet,
    ResolvedPostAnalysis,
)
from .llm_client import get_llm_triplets_async, resolve_entity_names_async
from .db import fetch_all_posts, create_triplets_table, insert_triplets_batch


async def run_parallel_extraction(db):
    """
    Main orchestration function that:
    1. Fetches all posts from the database
    2. Extracts triplets in parallel batches
    3. Resolves entity names
    4. Formats and persists results
    
    Args:
        db: Active SQLite database connection
    """
    # 1. Fetch data
    start_fetch = time.time()
    all_posts = await fetch_all_posts(db)
    batch_size = 25
    
    # 2. Create batches
    batches = [all_posts[i:i + batch_size] for i in range(0, len(all_posts), batch_size)]

    # 3. Execute all batches concurrently
    tasks = [get_llm_triplets_async(batch) for batch in batches]
    results = await asyncio.gather(*tasks)

    # 4. Flatten and process results
    all_extractions: List[PostAnalysis] = []
    for batch_result in results:
        all_extractions.extend(batch_result.results)
    
    # 5. Collect all unique canonical names from triplets
    canonical_names_set: set[str] = set()
    for extraction in all_extractions:
        for triplet in extraction.triplets:
            canonical_names_set.add(triplet.subject.canonical_name)
            canonical_names_set.add(triplet.object.canonical_name)
    
    canonical_names_list = list(canonical_names_set)
    
    # 6. Resolve entity names using LLM
    name_mapping = await resolve_entity_names_async(canonical_names_list)
    
    # 7. Format results with resolved canonical names
    resolved_extractions = format_resolved_extractions(all_extractions, name_mapping)
    
    # 8. Persist triplets to SQLite
    await persist_triplets_to_db(db, resolved_extractions)
    
    return resolved_extractions


async def parallel_extraction_stream(db):
    """
    Streaming version of run_parallel_extraction that yields progress events.
    
    Yields events at each stage:
    - extracting: Starting extraction from posts
    - batch_completed: Each batch completion update
    - building_entities: Building canonical entity list
    - storing: Storing entities and relationships
    
    Args:
        db: Active SQLite database connection
    """
    try:
        # 1. Fetch data
        all_posts = await fetch_all_posts(db)
        batch_size = 25
        
        # 2. Create batches
        batches = [all_posts[i:i + batch_size] for i in range(0, len(all_posts), batch_size)]
        # Count unique subreddits
        unique_subreddits = set(post["subreddit"] for post in all_posts)
        
        # Step 1: Starting extraction
        yield {
            "stage": "extracting",
            "message": f"Extracting Entities & Inferring Relationships from {len(all_posts)} posts across {len(unique_subreddits)} subreddits"
        }

        # 3. Execute batches with progress tracking
        total_batches = len(batches)
        completed_batches = 0
        
        # Process batches in parallel but track completion
        tasks = [get_llm_triplets_async(batch) for batch in batches]
        
        # Use asyncio.as_completed to track progress
        all_extractions: List[PostAnalysis] = []
        for coro in asyncio.as_completed(tasks):
            batch_result = await coro
            all_extractions.extend(batch_result.results)
            completed_batches += 1
            
            # Yield progress for each completed batch
            yield {
                "stage": "batch_completed",
                "message": f"Batch processing completed ({completed_batches}/{total_batches})",
                "completed": completed_batches,
                "total": total_batches
            }
        
        # Step 2: Building canonical entities
        yield {
            "stage": "building_entities",
            "message": "Building list of canonical entities"
        }
        
        # 5. Collect all unique canonical names from triplets
        canonical_names_set: set[str] = set()
        for extraction in all_extractions:
            for triplet in extraction.triplets:
                canonical_names_set.add(triplet.subject.canonical_name)
                canonical_names_set.add(triplet.object.canonical_name)
        
        canonical_names_list = list(canonical_names_set)
        
        # 6. Resolve entity names using LLM
        name_mapping = await resolve_entity_names_async(canonical_names_list)
        
        # 7. Format results with resolved canonical names
        resolved_extractions = format_resolved_extractions(all_extractions, name_mapping)
        
        # Step 3: Storing
        yield {
            "stage": "storing",
            "message": "Storing Entities & Relationships"
        }
        
        # 8. Persist triplets to SQLite
        await persist_triplets_to_db(db, resolved_extractions)
        
        # Write results to JSON file
        with open("extraction_results.json", "w") as f:
            json.dump([item.model_dump() for item in resolved_extractions], f, indent=2)
        
    except Exception as e:
        print(f"Error in parallel_extraction_stream: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def format_resolved_extractions(
    all_extractions: List[PostAnalysis],
    name_mapping: dict[str, str]
) -> List[ResolvedPostAnalysis]:
    """
    Transform raw extractions into resolved extractions using the entity name mapping.
    
    Args:
        all_extractions: List of raw post analyses with triplets
        name_mapping: Dictionary mapping canonical names to master names
        
    Returns:
        List of resolved post analyses with normalized entity names
    """
    resolved_extractions: List[ResolvedPostAnalysis] = []
    
    for extraction in all_extractions:
        resolved_triplets: List[ResolvedTriplet] = []
        for triplet in extraction.triplets:
            resolved_triplet = ResolvedTriplet(
                subject=name_mapping.get(triplet.subject.canonical_name, triplet.subject.canonical_name),
                relationship=triplet.relationship,
                object=name_mapping.get(triplet.object.canonical_name, triplet.object.canonical_name),
                evidence=triplet.evidence
            )
            resolved_triplets.append(resolved_triplet)
        
        resolved_extraction = ResolvedPostAnalysis(
            triplets=resolved_triplets,
            post_id=extraction.post_id,
            post_url=extraction.post_url,
            justification=extraction.justification
        )
        resolved_extractions.append(resolved_extraction)
    
    return resolved_extractions


async def persist_triplets_to_db(db, resolved_extractions: List[ResolvedPostAnalysis]):
    """
    Persist resolved triplets to SQLite database.
    
    Args:
        db: Active database connection
        resolved_extractions: List of resolved post analyses containing triplets to persist.
    """
    await create_triplets_table(db)
    
    # Prepare batch of triplets for insertion
    triplets_batch = []
    for extraction in resolved_extractions:
        for triplet in extraction.triplets:
            triplets_batch.append((
                triplet.subject,
                triplet.relationship,
                triplet.object,
                triplet.evidence,
                extraction.post_id,
                extraction.post_url,
                extraction.justification
            ))
    
    if triplets_batch:
        await insert_triplets_batch(db, triplets_batch)
