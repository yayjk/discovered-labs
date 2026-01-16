import json
import os
import re
from typing import List

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

load_dotenv()

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


def find_subreddits_via_reddit_posts_search(query: str, min_comments: int = 10) -> dict:
    """Fetch posts from `search query` and return a dict mapping `subreddit_name_prefixed` -> `subreddit_subscribers`.

    Rules:
    - Skip posts where `num_comments` is less than `min_comments`.
    - If a subreddit is already added, skip subsequent posts from the same subreddit.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    url="https://www.reddit.com/search.json?q={query}&sort=relevance&t=month&limit=25"

    try:
        resp = curl_requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch posts from Reddit: {exc}") from exc

    results: list = []

    for i, child in enumerate(payload.get("data", {}).get("children", [])):
        if not isinstance(child, dict):
            continue
        data = child.get("data", {})

        # Get subreddit identifier
        subreddit_prefixed = data.get("subreddit_name_prefixed")

        # Skip low-engagement posts
        try:
            num_comments = int(data.get("num_comments", 0))
        except (TypeError, ValueError):
            continue
        if num_comments < min_comments:
            continue

        if subreddit_prefixed and subreddit_prefixed not in results:
            results.append(subreddit_prefixed)

    return results


def aggregate_and_filter_subreddits(
    query: str,
    min_subscribers: int = 5000,
    timeout: int = 10,
    reddit_min_comments: int = 5,
    google_target_count: int = 20,
) -> dict:
    """Discover subreddits from Reddit posts, Gemini, and Google for `query`,
    deduplicate, then validate via each subreddit's `/about.json`.

    - `query` is used for all discovery methods.
    - Returns dict mapping normalized `r/Name` -> subscriber count (from about.json) for
      subreddits whose subscriber count is >= `min_subscribers` and whose `/about.json`
      is accessible.
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
        reddit_found = find_subreddits_via_reddit_posts_search(query, min_comments=reddit_min_comments)
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

    return combined


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
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"}

        # Use a single search call per subreddit to compute frequency, freshness, and engagement
        search_url = f"https://www.reddit.com/{subreddit}/search.json"
        params = {"q": query, "sort": "new", "restrict_sr": "1", "limit": 100}
        async with AsyncSession() as client:
            resp_search = await client.get(search_url, headers=headers, params=params, timeout=timeout)
            if resp_search.status_code == 200:
                json_response = resp_search.text  # Store the raw JSON response
                posts = resp_search.json().get("data", {}).get("children", [])
                q_lower = (query or "").lower()
                pattern = re.compile(re.escape(q_lower))
                cutoff = now - (48 * 3600)
                for p in posts:
                    data = p.get("data", {})
                    title_lower = (data.get("title") or "").lower()
                    selftext_lower = (data.get("selftext") or "").lower()
                    text = title_lower + " " + selftext_lower

                    # Frequency: count occurrences of query in title+selftext
                    frequency += len(pattern.findall(text))

                    # Votes for engagement
                    ups = data.get("ups") or 0
                    downs = data.get("downs") or 0
                    num_comments = data.get("num_comments") or 0
                    try:
                        total_votes += int(ups) + abs(int(downs))
                        total_comments += int(num_comments)
                        vote_counted_posts += 1
                    except Exception:
                        pass

                    # Freshness: posts in last 48 hours
                    created = data.get("created_utc")
                    try:
                        if created and float(created) >= cutoff:
                            freshness += 1
                    except Exception:
                        pass
            else:
                print(f"Failed to fetch posts for {subreddit}, status code: {resp_search.status_code}")
                json_response = None

        engagement_raw = ((total_votes + total_comments) / subs) * 1000 if subs and subs > 0 else 0

        print(f"Subreddit: {subreddit}, Subs: {subs}, Freq: {frequency}, Fresh: {freshness}, Eng: {engagement_raw:.2f}")
        # Insert into DB
        await insert_subreddit(db_conn, subreddit, json_response, engagement_raw, freshness, frequency, subs)

    except Exception as e:
        print(f"Error processing {subreddit}: {e}")


async def score_and_rank_subreddits_async(
    query: str,
    min_frequency: int = 3,
    min_subscribers: int = 5000,
    timeout: int = 10,
    reddit_min_comments: int = 5,
    google_target_count: int = 10,
) -> list:
    """Discover subreddits for `query`, score and rank them asynchronously.

    Returns a list of dicts sorted by composite score (descending). Each dict contains:
    - subreddit, subscribers, frequency, freshness, engagement, relevance_score
    """
    # Discover subreddits internally
    subreddits = aggregate_and_filter_subreddits(
        query,
        min_subscribers=min_subscribers,
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

    # Create tasks for all subreddits
    tasks = []
    for subreddit, subs in subreddits.items():
        task = calculate_and_insert_subreddit_score(db_conn, subreddit, subs, query, timeout, now)
        tasks.append(task)

    # Run all tasks concurrently
    await asyncio.gather(*tasks)

    # Fetch all scores from DB
    rows = await select_subreddits_by_frequency(db_conn, min_frequency)

    if not rows:
        await db_conn.close()
        return []

    # Extract scores for normalization
    freq_map = {row[0]: row[3] for row in rows}
    fresh_map = {row[0]: row[2] for row in rows}
    eng_map = {row[0]: row[1] for row in rows}
    subs_map = {row[0]: row[4] for row in rows}

    # Normalize using max-scaling
    def normalize_map(m: dict) -> dict:
        if not m:
            return {}
        max_val = max(m.values())
        if not max_val:
            return {k: 0.0 for k in m}
        return {k: float(v) / float(max_val) for k, v in m.items()}

    norm_freq = normalize_map(freq_map)
    norm_subs = normalize_map(subs_map)
    norm_fresh = normalize_map(fresh_map)
    norm_eng = normalize_map(eng_map)

    # Calculate relevance_score and update DB
    for sub in freq_map.keys():
        score = (
            0.4 * norm_freq.get(sub, 0.0)
            + 0.1 * norm_subs.get(sub, 0.0)
            + 0.3 * norm_fresh.get(sub, 0.0)
            + 0.2 * norm_eng.get(sub, 0.0)
        )
        relevance_score = score * 100
        await update_relevance_score(db_conn, sub, relevance_score)

    print("Relevance scores updated for all subreddits")

    # Fetch all with relevance_score, sort by relevance_score desc
    all_rows = await select_all_subreddits_ordered(db_conn)

    print("Top 5 subreddits by relevance:")
    for row in all_rows[:5]:
        print(f"  {row[0]}: {row[6]:.2f}")

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
    min_subscribers: int = 5000,
    timeout: int = 10,
    reddit_min_comments: int = 5,
    google_target_count: int = 10,
):
    """Discover subreddits for `query`, score and rank them.

    This function calls the async version for optimized batch processing.

    Returns the db connection.
    """
    return asyncio.run(score_and_rank_subreddits_async(
        query, min_frequency, min_subscribers, timeout, reddit_min_comments, google_target_count
    ))


__all__ = ["score_and_rank_subreddits"]

