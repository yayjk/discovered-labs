"""Core community finder utilities for subreddit discovery and scoring."""

import os
import re
import time
import asyncio
import random
from typing import List

from dotenv import load_dotenv
import instructor
import httpx

from .constants import GOOGLE_SEARCH_URL
from .models import SubredditDiscovery, SubredditPost, RedditScrapeSource
from .prompts import get_subreddit_finder_prompt
from .db import (
    insert_subreddit,
    init_subreddits_db,
    select_subreddits_by_frequency,
    select_all_subreddits_ordered,
    update_relevance_score,
    delete_subreddits_by_names,
    update_json_response_null,
)
from .helpers import add_jitter
from .subreddit_discovery import scrape_reddit_search
from .legacy import find_subreddits_via_reddit_posts_search

load_dotenv()


def deduplicate_subreddits(subreddits: List[str]) -> SubredditDiscovery:
    """
    Remove duplicates and normalize subreddit names.
    
    Args:
        subreddits: List of subreddit names (may contain duplicates and various formats)
        
    Returns:
        SubredditDiscovery with normalized, deduplicated subreddit names
    """
    def normalize_name(x: str) -> str | None:
        if not x or not isinstance(x, str):
            return None
        if x.startswith("/r/"):
            return x[1:].lower()
        if x.startswith("r/"):
            return x.lower()
        return f"r/{x.strip().lower()}"

    normalized_set: set[str] = set()
    
    for subreddit in subreddits:
        normalized = normalize_name(subreddit)
        if normalized:
            normalized_set.add(normalized)
    
    return SubredditDiscovery(subreddits=list(normalized_set))


async def calculate_and_insert_subreddit_score(
    db_conn,
    subreddit: str,
    posts: List[SubredditPost],
    query: str,
):
    """
    Calculate scores for a subreddit based on posts and insert into DB.
    
    Args:
        db_conn: Database connection
        subreddit: Subreddit name (e.g., 'r/python')
        posts: List of SubredditPost objects
        query: The search query used for frequency calculation
    """
    try:
        now = time.time()
        frequency = 0
        total_votes = 0
        total_comments = 0
        vote_counted_posts = 0
        freshness = 0
        
        if posts:
            json_response = str([p.model_dump() for p in posts])  # Store as string representation
            q_lower = (query or "").lower()
            pattern = re.compile(re.escape(q_lower))
            cutoff = now - (48 * 3600)
            
            for post in posts:
                title_lower = (post.post_title or "").lower()
                selftext_lower = (post.self_text or "").lower()
                text = title_lower + " " + selftext_lower

                # Frequency: count occurrences of query in title+selftext
                frequency += len(pattern.findall(text))

                # Votes for engagement
                try:
                    ups = int(post.ups or 0)
                    num_comments = int(post.num_comments or 0)
                    total_votes += ups
                    total_comments += num_comments
                    vote_counted_posts += 1
                except Exception:
                    pass

                # Freshness: posts in last 48 hours
                created_datetime = post.created_datetime
                try:
                    if created_datetime:
                        # Parse ISO format datetime
                        from datetime import datetime
                        created_time = datetime.fromisoformat(created_datetime.replace('Z', '+00:00')).timestamp()
                        if created_time >= cutoff:
                            freshness += 1
                except Exception:
                    pass
        else:
            json_response = None

        # Engagement is total votes + comments
        engagement_raw = total_votes + total_comments
        
        # Insert into DB
        await insert_subreddit(db_conn, subreddit, json_response, engagement_raw, freshness, frequency)

    except Exception as e:
        print(f"Error processing {subreddit}: {e}")


def find_subreddits_via_gemini(topic: str) -> SubredditDiscovery:
    """
    Find subreddits for a topic using Gemini via OpenRouter.
    
    Args:
        topic: The topic to find subreddits for
        
    Returns:
        SubredditDiscovery object with list of subreddits
    """
    if not topic or not topic.strip():
        return SubredditDiscovery()

    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("SUBREDDIT_FINDER_MODEL", "openrouter/google/gemini-2.5-flash")

    prompt = get_subreddit_finder_prompt(topic)

    try:
        mode = instructor.Mode.OPENROUTER_STRUCTURED_OUTPUTS
        client = instructor.from_provider(model, api_key=api_key, mode=mode)
        
        parsed_obj = client.create(
            response_model=SubredditDiscovery, 
            messages=[{"role": "user", "content": prompt}], 
            max_retries=2
        )
        return parsed_obj
    except Exception as exc:
        print(f"Error fetching subreddits: {exc}")
        return SubredditDiscovery()


def find_subreddits_via_google(query: str, target_count: int = 20) -> List[str]:
    """
    Find subreddits for a query using Google Custom Search API.
    
    Args:
        query: The search query
        target_count: Target number of subreddits to find
        
    Returns:
        List of subreddit names
    """
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx_id = os.getenv("GOOGLE_SEARCH_CX")
    
    search_query = f'{query} site:reddit.com/r/'
    
    discovered_subs = set()
    
    # Loop to get up to 40-50 results (10 per page)
    for start in range(1, 41, 10):
        params = {
            "key": api_key,
            "cx": cx_id,
            "q": search_query,
            "num": 10,
            "start": start,
            "sort": "date",
            "dateRestrict": "m6"
        }

        try:
            response = httpx.get(GOOGLE_SEARCH_URL, params=params)
            if response.status_code != 200:
                break
            
            items = response.json().get("items", [])
            for item in items:
                link = item.get("link", "")
                
                # SKIP translations (tl=) and user profiles (u/)
                if "?tl=" in link or "/u/" in link:
                    continue
                
                # Extract r/name
                match = re.search(r"(r/[a-zA-Z0-9_]+)", link)
                if match:
                    sub = match.group(1).lower()
                    
                    # Skip system subs
                    if sub not in ["r/u", "r/reddit", "r/all"]:
                        discovered_subs.add(sub)
            
            # Stop if we have enough
            if len(discovered_subs) >= target_count:
                break
                
            time.sleep(0.5)  # Anti-throttle
            
        except Exception as e:
            print(f"Discovery Error: {e}")
            break
            
    return list(discovered_subs)


def aggregate_and_filter_subreddits(
    query: str,
    reddit_min_comments: int = 5,
    google_target_count: int = 20,
    reddit_scrape_source: RedditScrapeSource = RedditScrapeSource.HTML,
) -> SubredditDiscovery:
    """
    Discover subreddits from Reddit posts, Gemini, and Google for a query, and deduplicate.

    Args:
        query: The search query
        reddit_min_comments: Minimum comments for Reddit results
        google_target_count: Target count for Google results
        reddit_scrape_source: Source for Reddit scraping ("html" or "api")
        
    Returns:
        DiscoveredSubreddits with list of normalized subreddit names
    """
    combined: List[str] = []

    # Discover via reddit posts (using specified source)
    try:
        if reddit_scrape_source == RedditScrapeSource.HTML:
            reddit_found = scrape_reddit_search(query)
        else:
            reddit_found = find_subreddits_via_reddit_posts_search(query, min_comments=reddit_min_comments)
        
        combined.extend(reddit_found)
    except Exception as exc:
        print(f"reddit discovery failed: {exc}")

    # Discover via Gemini (instructor)
    try:
        gemini_obj = find_subreddits_via_gemini(query)
        gemini_list = []
        if hasattr(gemini_obj, "subreddits"):
            gemini_list = getattr(gemini_obj, "subreddits") or []
        combined.extend(gemini_list)
    except Exception as exc:
        print(f"gemini discovery failed: {exc}")

    # Discover via Google
    try:
        google_list = find_subreddits_via_google(query, target_count=google_target_count) or []
        combined.extend(google_list)
    except Exception as exc:
        print(f"google discovery failed: {exc}")

    # Use core function to deduplicate and normalize
    return deduplicate_subreddits(combined)


async def score_and_rank_subreddits_async(
    discovery_result: SubredditDiscovery,
    process_subreddit,
    query: str,
    min_frequency: int = 3,
):
    """
    Score and rank discovered subreddits asynchronously.
    
    Uses batched concurrent calls (2-4 random simultaneous calls) with jitter between batches
    to avoid detection and rate limiting.

    Args:
        discovery_result: SubredditDiscovery object with discovered subreddits
        process_subreddit: Async callable that processes a single subreddit
        query: The search query
        min_frequency: Minimum frequency score to include
        
    Returns:
        Database connection with ranked subreddits
    """
    subreddits = discovery_result.subreddits

    if not subreddits:
        return []

    # Initialize in-memory DB
    db_conn = await init_subreddits_db()

    # Process subreddits in batches with random concurrency (2-4 per batch)
    i = 0
    batch_num = 1
    while i < len(subreddits):
        # Random batch size for each iteration
        batch_size = random.randint(2, 4)
        batch = subreddits[i:i + batch_size]
        
        if not batch:
            break
        
        # Create tasks for this batch
        batch_tasks = [process_subreddit(subreddit, db_conn) for subreddit in batch]
        
        # Run batch concurrently
        await asyncio.gather(*batch_tasks)
        
        i += len(batch)
        batch_num += 1
        
        # Add jitter between batches (if not the last batch)
        if i < len(subreddits):
            await add_jitter(min_delay=1.5, max_delay=3.5)

    # Fetch all scores from DB
    rows = await select_subreddits_by_frequency(db_conn, min_frequency)

    if not rows:
        await db_conn.close()
        return []

    # Extract scores for normalization
    freq_map = {row[0]: row[3] for row in rows}
    fresh_map = {row[0]: row[2] for row in rows}
    eng_map = {row[0]: row[1] for row in rows}

    # Normalize using max-scaling
    def normalize_map(m: dict) -> dict:
        if not m:
            return {}
        max_val = max(m.values())
        if not max_val:
            return {k: 0.0 for k in m}
        return {k: float(v) / float(max_val) for k, v in m.items()}

    norm_freq = normalize_map(freq_map)
    norm_fresh = normalize_map(fresh_map)
    norm_eng = normalize_map(eng_map)

    # Calculate relevance_score and update DB
    for sub in freq_map.keys():
        score = (
            0.4 * norm_freq.get(sub, 0.0)
            + 0.3 * norm_fresh.get(sub, 0.0)
            + 0.3 * norm_eng.get(sub, 0.0)
        )
        relevance_score = score * 100
        await update_relevance_score(db_conn, sub, relevance_score)

    # Fetch all with relevance_score, sort by relevance_score desc
    all_rows = await select_all_subreddits_ordered(db_conn)

    # Keep top 20
    top_20 = all_rows[:20]

    # Delete subreddits not in top 20
    if len(all_rows) > 20:
        bottom_subs = [row[0] for row in all_rows[20:]]
        await delete_subreddits_by_names(db_conn, bottom_subs)

    # For subreddits not in top 5, remove json_response
    if len(top_20) > 5:
        for i in range(5, len(top_20)):
            await update_json_response_null(db_conn, top_20[i][0])

    # Fetch final top 20
    final_rows = await select_all_subreddits_ordered(db_conn)

    return db_conn


async def score_and_rank_subreddits_stream(
    discovery_result: SubredditDiscovery,
    process_subreddit_func,
    query: str,
    min_frequency: int = 3,
):
    """
    Score and rank discovered subreddits with streaming progress events.
    
    Yields progress events at each stage:
    - processing_batch: When processing each batch of subreddits
    - saving: When saving data to database
    
    Args:
        discovery_result: SubredditDiscovery object with discovered subreddits
        process_subreddit_func: Async callable that processes a single subreddit and returns posts
        query: The search query
        min_frequency: Minimum frequency score to include
        
    Yields:
        Dict events with stage and message information
    """
    from .helpers import process_json_responses
    
    # Step 1: Ranking subreddits
    yield {"stage": "ranking", "message": "Ranking subreddits based on relevance..."}
    
    # Initialize in-memory DB
    db_conn = await init_subreddits_db()
    
    subreddits = discovery_result.subreddits
    
    # Process subreddits in batches with events
    i = 0
    batch_num = 1
    while i < len(subreddits):
        # Random batch size for each iteration
        batch_size = random.randint(2, 4)
        batch = subreddits[i:i + batch_size]
        
        if not batch:
            break
        
        # Yield batch processing event
        batch_list = ", ".join(batch)
        yield {
            "stage": "processing_batch",
            "message": f"Processing batch {batch_num}: [{batch_list}]",
            "batch_number": batch_num,
            "subreddits": batch
        }
        
        # Process each subreddit in the batch
        batch_tasks = []
        for subreddit in batch:
            try:
                # Get posts from the provided function
                posts = await process_subreddit_func(subreddit)
                
                # Call the core function with the fetched posts
                batch_tasks.append(calculate_and_insert_subreddit_score(
                    db_conn=db_conn,
                    subreddit=subreddit,
                    posts=posts,
                    query=query,
                ))
            except Exception as e:
                print(f"Error processing {subreddit}: {e}")
        
        # Run batch concurrently
        await asyncio.gather(*batch_tasks)
        
        i += len(batch)
        batch_num += 1
        
        # Add jitter between batches (if not the last batch)
        if i < len(subreddits):
            await add_jitter(min_delay=1.5, max_delay=3.5)
    
    # Continue with scoring and ranking
    rows = await select_subreddits_by_frequency(db_conn, min_frequency)
    
    if rows:
        # Extract scores for normalization
        freq_map = {row[0]: row[3] for row in rows}
        fresh_map = {row[0]: row[2] for row in rows}
        eng_map = {row[0]: row[1] for row in rows}

        # Normalize using max-scaling
        def normalize_map(m: dict) -> dict:
            if not m:
                return {}
            max_val = max(m.values())
            if not max_val:
                return {k: 0.0 for k in m}
            return {k: float(v) / float(max_val) for k, v in m.items()}

        norm_freq = normalize_map(freq_map)
        norm_fresh = normalize_map(fresh_map)
        norm_eng = normalize_map(eng_map)

        # Calculate relevance_score and update DB
        for sub in freq_map.keys():
            score = (
                0.4 * norm_freq.get(sub, 0.0)
                + 0.3 * norm_fresh.get(sub, 0.0)
                + 0.3 * norm_eng.get(sub, 0.0)
            )
            relevance_score = score * 100
            await update_relevance_score(db_conn, sub, relevance_score)

        # Fetch all with relevance_score, sort by relevance_score desc
        all_rows = await select_all_subreddits_ordered(db_conn)

        # Keep top 20
        top_20 = all_rows[:20]

        # Delete subreddits not in top 20
        if len(all_rows) > 20:
            bottom_subs = [row[0] for row in all_rows[20:]]
            await delete_subreddits_by_names(db_conn, bottom_subs)

        # For subreddits not in top 5, remove json_response
        if len(top_20) > 5:
            for i in range(5, len(top_20)):
                await update_json_response_null(db_conn, top_20[i][0])
    
    # Step 2: Saving data
    yield {"stage": "saving", "message": "Processing and saving data to database..."}
    
    db_conn = await process_json_responses(db_conn, query)
    
    # Yield internal event with db_conn for next phase
    yield {
        "stage": "_internal_db_conn",
        "db_conn": db_conn
    }


__all__ = [
    "deduplicate_subreddits",
    "calculate_and_insert_subreddit_score",
    "find_subreddits_via_gemini",
    "find_subreddits_via_google",
    "aggregate_and_filter_subreddits",
    "score_and_rank_subreddits_async",
    "score_and_rank_subreddits_stream",
]
