import json
import os
import re
from typing import List
import random

from dotenv import load_dotenv
import instructor
import httpx
from curl_cffi import requests as curl_requests
from curl_cffi.requests import AsyncSession
import urllib.parse
import time
import asyncio
from pydantic import BaseModel, Field

from .db import (
    get_db,
    create_subreddits_table,
    insert_subreddit,
    select_subreddits_by_frequency,
    select_all_subreddits_ordered,
    update_relevance_score,
    delete_subreddits_by_names,
    update_json_response_null,
    close_db,
)
from .subredditDiscovery import scrape_reddit_search
from .subredditRanking import scrape_subreddit_search

load_dotenv()

# Browser user agents for rotation
USER_AGENTS = {
    "chrome_131": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "chrome_130": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "firefox_latest": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "safari_macos": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "edge_131": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "chrome_mobile": "Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
}

async def add_jitter(min_delay: float = 0.5, max_delay: float = 2.5):
    """
    Add random jitter (delay) between requests to avoid detection.
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
    """
    jitter = random.uniform(min_delay, max_delay)
    await asyncio.sleep(jitter)


class SubredditDiscovery(BaseModel):
    subreddits: List[str] = []

def find_subreddits_via_gemini(topic: str) -> SubredditDiscovery:
    if not topic or not topic.strip():
        return SubredditDiscovery()

    api_key = os.getenv("OPENROUTER_API_KEY")
    # Using a model specialized for search/retrieval
    model = os.getenv("SUBREDDIT_FINDER_MODEL", "openrouter/google/gemini-2.5-flash")

    prompt = (
        f"Identify the 10 most active and relevant subreddits for the topic: '{topic}'. "
        "Focus on communities where users discuss breaking updates, latest news, or current events. "
        "Return the data as a JSON object with a list of 'subreddits', each containing 'name' (with r/)."
    )

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


def find_subreddits_via_google(query: str, target_count: int = 20):
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx_id = os.getenv("GOOGLE_SEARCH_CX")
    
    # We remove the '-inurl:comments' to allow more leads, 
    # but we add a 'intitle' check for high relevance.
    search_query = f'{query} site:reddit.com/r/'
    url = "https://www.googleapis.com/customsearch/v1"
    
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
            response = httpx.get(url, params=params)
            if response.status_code != 200: break
            
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
                
            time.sleep(0.5) # Anti-throttle
            
        except Exception as e:
            print(f"Discovery Error: {e}")
            break
            
    return list(discovered_subs)


def aggregate_and_filter_subreddits(
    query: str,
    timeout: int = 10,
    reddit_min_comments: int = 5,
    google_target_count: int = 20,
) -> list:
    """Discover subreddits from Reddit posts, Gemini, and Google for `query`,
    and deduplicate.

    - `query` is used for all discovery methods.
    - Returns list of normalized subreddit names
    """

    def normalize_name(x: str) -> str | None:
        if not x or not isinstance(x, str):
            return None
        if x.startswith("/r/"):
            return x[1:].lower()
        if x.startswith("r/"):
            return x.lower()
        return f"r/{x.strip().lower()}"

    combined: set[str] = set()

    # Discover via reddit posts
    try:
        reddit_found = scrape_reddit_search(query)
        for item in reddit_found:
            n = normalize_name(item)
            if n:
                combined.add(n)
    except Exception as exc:
        # keep going even if reddit search fails
        print(f"reddit discovery failed: {exc}")

    # Discover via Gemini (instructor)
    try:
        gemini_obj = find_subreddits_via_gemini(query)
        gemini_list = []
        if hasattr(gemini_obj, "subreddits"):
            gemini_list = getattr(gemini_obj, "subreddits") or []
        for item in gemini_list:
            n = normalize_name(item)
            if n:
                combined.add(n)
    except Exception as exc:
        print(f"gemini discovery failed: {exc}")

    # Discover via Google
    try:
        google_list = find_subreddits_via_google(query, target_count=google_target_count) or []
        for item in google_list:
            n = normalize_name(item)
            if n:
                combined.add(n)
    except Exception as exc:
        print(f"google discovery failed: {exc}")

    return list(combined)


async def init_subreddits_db():
    """Initialize in-memory SQLite database for subreddits."""
    db_conn = await get_db()
    await create_subreddits_table(db_conn)
    return db_conn


async def calculate_and_insert_subreddit_score(db_conn, subreddit: str, subs: int, query: str, timeout: int, now: float):
    """Async method to calculate scores for a subreddit and insert into DB."""
    try:
        frequency = 0
        total_votes = 0
        total_comments = 0
        vote_counted_posts = 0
        freshness = 0
        
        # Extract subreddit name (remove r/ if present)
        sub_name = subreddit.replace('r/', '').replace('/', '')
        
        # Use scrape_subreddit_search to get posts
        posts = scrape_subreddit_search(subreddit=sub_name, query=query, max_pages=1)
        
        if posts:
            json_response = str(posts)  # Store as string representation
            q_lower = (query or "").lower()
            pattern = re.compile(re.escape(q_lower))
            cutoff = now - (48 * 3600)
            
            for post in posts:
                title_lower = (post.get("post_title") or "").lower()
                selftext_lower = (post.get("self_text") or "").lower()
                text = title_lower + " " + selftext_lower

                # Frequency: count occurrences of query in title+selftext
                frequency += len(pattern.findall(text))

                # Votes for engagement
                try:
                    ups = int(post.get("ups", 0) or 0)
                    num_comments = int(post.get("num_comments", 0) or 0)
                    total_votes += ups
                    total_comments += num_comments
                    vote_counted_posts += 1
                except Exception:
                    pass

                # Freshness: posts in last 48 hours
                created_datetime = post.get("created_datetime")
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

        print(f"Subreddit: {subreddit}, Freq: {frequency}, Fresh: {freshness}, Eng: {engagement_raw}")
        # Insert into DB
        await insert_subreddit(db_conn, subreddit, json_response, engagement_raw, freshness, frequency)

    except Exception as e:
        print(f"Error processing {subreddit}: {e}")


async def score_and_rank_subreddits_async(
    query: str,
    min_frequency: int = 3,
    timeout: int = 10,
    reddit_min_comments: int = 5,
    google_target_count: int = 10,
) -> list:
    """Discover subreddits for `query`, score and rank them asynchronously.
    
    Uses batched concurrent calls (2-4 random simultaneous calls) with jitter between batches
    to avoid detection and rate limiting.

    Returns a list of dicts sorted by composite score (descending). Each dict contains:
    - subreddit, frequency, freshness, engagement, relevance_score
    """
    # Discover subreddits internally
    subreddits = aggregate_and_filter_subreddits(
        query,
        timeout=timeout,
        reddit_min_comments=reddit_min_comments,
        google_target_count=google_target_count,
    )

    if not subreddits:
        return []

    # Initialize in-memory DB
    db_conn = await init_subreddits_db()

    now = time.time()
    print(f"Discovered {len(subreddits)} subreddits for query '{query}'")

    # Process subreddits in batches with random concurrency (2-4 per batch)
    i = 0
    batch_num = 1
    while i < len(subreddits):
        # Random batch size for each iteration
        batch_size = random.randint(2, 4)
        batch = subreddits[i:i + batch_size]
        
        if not batch:
            break
        
        print(f"\nProcessing batch {batch_num}: {len(batch)} subreddits (batch_size={batch_size})")
        
        # Create tasks for this batch
        batch_tasks = [
            calculate_and_insert_subreddit_score(db_conn, subreddit, 0, query, timeout, now)
            for subreddit in batch
        ]
        
        # Run batch concurrently
        await asyncio.gather(*batch_tasks)
        
        i += len(batch)
        batch_num += 1
        
        # Add jitter between batches (if not the last batch)
        if i < len(subreddits):
            await add_jitter(min_delay=1.5, max_delay=3.5)
            print("Added jitter between batches")

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

    print("Relevance scores updated for all subreddits")

    # Fetch all with relevance_score, sort by relevance_score desc
    all_rows = await select_all_subreddits_ordered(db_conn)

    print("Top 5 subreddits by relevance:")
    for row in all_rows[:5]:
        print(f"  {row[0]}: {row[5]:.2f}")

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


def score_and_rank_subreddits(
    query: str,
    min_frequency: int = 3,
    timeout: int = 10,
    reddit_min_comments: int = 5,
    google_target_count: int = 10,
):
    """Discover subreddits for `query`, score and rank them.

    This function calls the async version for optimized batch processing.

    Returns the db connection.
    """
    return asyncio.run(score_and_rank_subreddits_async(
        query, min_frequency, timeout, reddit_min_comments, google_target_count
    ))


__all__ = ["score_and_rank_subreddits"]

