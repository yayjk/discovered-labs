"""Community finder module for discovering and ranking subreddits."""

import asyncio
import json
from pathlib import Path
from typing import List

from .db import init_subreddits_db
from .models import SubredditDiscovery, RedditScrapeSource
from .subreddit_ranking import get_relevant_posts_from_subreddit
from .legacy import (
    get_relevant_posts_from_subreddit_api,
    test_find_subreddits_via_reddit_posts_search_json,
    test_get_relevant_posts_from_subreddit_api_json,
)
from .core import (
    calculate_and_insert_subreddit_score,
    aggregate_and_filter_subreddits,
    score_and_rank_subreddits_async,
    score_and_rank_subreddits_stream,
    deduplicate_subreddits,
)


async def score_and_rank_subreddits(
    query: str,
    min_frequency: int = 3,
    timeout: int = 10,
    reddit_min_comments: int = 5,
    google_target_count: int = 10,
    reddit_scrape_source: RedditScrapeSource = RedditScrapeSource.HTML,
):
    """
    Discover subreddits for a query, score and rank them.

    Args:
        query: The search query
        min_frequency: Minimum frequency score to include
        timeout: Request timeout in seconds
        reddit_min_comments: Minimum comments for Reddit results
        google_target_count: Target count for Google results
        reddit_scrape_source: Source for Reddit scraping ("html" or "api")
        
    Returns:
        Database connection with ranked subreddits
    """
    from .helpers import process_json_responses
    
    # Discover subreddits
    discovery_result = aggregate_and_filter_subreddits(
        query,
        reddit_min_comments=reddit_min_comments,
        google_target_count=google_target_count,
        reddit_scrape_source=reddit_scrape_source,
    )
    
    # This will be called with db_conn from score_and_rank_subreddits_async
    async def process_subreddit(subreddit: str, db_conn):
        try:
            # Fetch posts based on reddit_scrape_source
            if reddit_scrape_source == RedditScrapeSource.API:
                posts = await get_relevant_posts_from_subreddit_api(subreddit=subreddit, query=query, timeout=timeout)
            else:
                posts = get_relevant_posts_from_subreddit(subreddit=subreddit, query=query, max_pages=1)
            
            # Call the core function with the fetched posts
            await calculate_and_insert_subreddit_score(
                db_conn=db_conn,
                subreddit=subreddit,
                posts=posts or [],
                query=query,
            )
        except Exception as e:
            print(f"Error processing {subreddit}: {e}")
    
    # Run score_and_rank_subreddits_async
    db_conn = await score_and_rank_subreddits_async(
        discovery_result,
        process_subreddit,
        query,
        min_frequency,
    )
    
    # Process JSON responses and migrate to posts table
    await process_json_responses(db_conn, query)
    
    return db_conn


async def test_aggregate_subreddits_stream():
    """
    Test aggregate and filter subreddits using local JSON files with streaming events.
    
    Reads Google, Gemini, and Reddit search results from archive files,
    combines them, and deduplicates.
    
    Yields events at each stage:
    - crawling_reddit: Reading Reddit search results from archive
    - searching_google: Reading Google search results from archive
    - asking_gemini: Reading Gemini recommendations from archive
    - aggregating: Combining and deduplicating results
    - aggregated: Shows discovered subreddits
    """
    # Step 1: Crawling Reddit
    yield {"stage": "crawling_reddit", "message": "Crawling Reddit search results..."}
    
    archive_dir = Path(__file__).parent / "archive"
    combined: List[str] = []
    
    # Read Reddit search results
    try:
        reddit_file = str(archive_dir / "testRedditSearch.json")
        reddit_results = test_find_subreddits_via_reddit_posts_search_json(reddit_file, min_comments=5)
        combined.extend(reddit_results)
    except Exception as e:
        pass
    
    # Step 2: Searching Google
    yield {"stage": "searching_google", "message": "Searching Google for subreddits..."}
    
    try:
        google_file = archive_dir / "testGoogleSearch.json"
        with open(google_file, "r", encoding="utf-8") as f:
            google_results = json.load(f)
            combined.extend(google_results)
    except Exception as e:
        pass
    
    # Step 3: Asking Gemini
    yield {"stage": "asking_gemini", "message": "Asking Gemini for recommendations..."}
    
    try:
        gemini_file = archive_dir / "testGeminiSearch.json"
        with open(gemini_file, "r", encoding="utf-8") as f:
            gemini_results = json.load(f)
            combined.extend(gemini_results)
    except Exception as e:
        pass
    
    # Step 4: Aggregating results
    yield {"stage": "aggregating", "message": "Aggregating results from all sources..."}
    
    # Deduplicate and normalize
    deduplicated = deduplicate_subreddits(combined)
    
    # Step 5: Report aggregated results
    subreddit_list = ", ".join(deduplicated.subreddits[:10]) if len(deduplicated.subreddits) <= 10 else ", ".join(deduplicated.subreddits[:10]) + f" and {len(deduplicated.subreddits) - 10} more"
    yield {
        "stage": "aggregated",
        "message": f"{len(deduplicated.subreddits)} aggregated results found: {subreddit_list}",
        "count": len(deduplicated.subreddits),
        "subreddits": deduplicated.subreddits
    }
    
    # Return the discovery result separately (not serialized to JSON)
    yield {
        "stage": "_internal_result",
        "discovery_result": deduplicated
    }


async def test_score_and_rank_subreddits_streaming():
    """
    Streaming version that yields progress events at each stage.
    
    Yields events at each stage:
    - crawling_reddit: Reading Reddit search results from archive
    - searching_google: Reading Google search results from archive  
    - asking_gemini: Reading Gemini recommendations from archive
    - aggregating: Combining and deduplicating results
    - aggregated: Shows discovered subreddits
    - ranking: Scoring and ranking subreddits
    - processing_batch: Processing each batch of subreddits
    - saving: Saving data to database
    - complete: Analysis finished
    """
    archive_dir = Path(__file__).parent / "archive"
    discovery_result = None
    db_conn = None
    
    # Step 1-5: Use streaming aggregation function and yield its events
    async for event in test_aggregate_subreddits_stream():
        # Don't yield internal events
        if event.get("stage") == "_internal_result":
            discovery_result = event.get("discovery_result")
        else:
            yield event
    
    # Function to load posts from archive for a subreddit
    async def load_posts_from_archive(subreddit: str):
        """Load posts from archive file for a given subreddit."""
        # Extract subreddit name for file lookup (remove r/ prefix)
        sub_name = subreddit.replace('r/', '').replace('/', '')
        
        # Load posts from archive file
        posts_file = archive_dir / f"{sub_name}.json"
        
        if posts_file.exists():
            return test_get_relevant_posts_from_subreddit_api_json(str(posts_file))
        return []
    
    # Step 6-7: Call core streaming function and yield its events
    async for event in score_and_rank_subreddits_stream(
        discovery_result=discovery_result,
        process_subreddit_func=load_posts_from_archive,
        query="openai",
        min_frequency=3,
    ):
        # Capture db_conn but don't yield internal event
        if event.get("stage") == "_internal_db_conn":
            db_conn = event.get("db_conn")
        else:
            yield event
    
    # Step 8: Yield internal event with db_conn for extraction phase
    yield {
        "stage": "_internal_db_conn",
        "db_conn": db_conn
    }
    
    # Step 9: Complete discovery phase
    yield {"stage": "discovery_complete", "message": "Community Discovery & ranking complete!", "success": True}


__all__ = [
    "score_and_rank_subreddits",
    "score_and_rank_subreddits_async",
    "test_aggregate_subreddits_stream",
    "test_score_and_rank_subreddits_streaming",
]
