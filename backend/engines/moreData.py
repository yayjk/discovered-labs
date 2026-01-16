import asyncio
import json
import os
from typing import List, Dict, Any

import httpx
from dotenv import load_dotenv

from .db import insert_post

load_dotenv()

async def fetch_paginated_posts(subreddit: str, query: str, after: str, headers: dict, db_conn, timeout: int = 10):
    """Fetch posts for a subreddit starting from after key."""
    print(f"Fetching paginated posts for {subreddit} with after: {after}")
    try:
        search_url = f"https://www.reddit.com/{subreddit}/search.json"
        params = {"q": query, "sort": "new", "restrict_sr": "1", "limit": 100}
        if after:
            params["after"] = after

        async with httpx.AsyncClient() as client:
            resp = await client.get(search_url, headers=headers, params=params, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                posts = data['data']['children']
                print(f"Retrieved {len(posts)} posts for {subreddit}")
                for child in posts:
                    post = child['data']
                    await insert_post(db_conn, subreddit, post['title'], post.get('selftext', ''), post['ups'], post['downs'], post['num_comments'], post['created_utc'], post['url'], post['id'])
                print(f"Inserted {len(posts)} posts into DB for {subreddit}")
                return data['data']['after']
            else:
                print(f"HTTP error {resp.status_code} for {subreddit}")
                return None
    except Exception as e:
        print(f"Error fetching paginated posts for {subreddit}: {e}")
        return None

def create_batches(posts: List[Dict[str, Any]], batch_size: int = 50) -> List[List[Dict[str, Any]]]:
    """Split posts into batches of specified size."""
    return [posts[i:i + batch_size] for i in range(0, len(posts), batch_size)]

async def process_batches(batches: List[List[Dict[str, Any]]]):
    """Placeholder async function to process batches simultaneously.
    
    This will be implemented later to make 20 simultaneous calls using openrouter/instructor & pydantic schema.
    """
    # Placeholder: for now, just print the number of batches
    print(f"Processing {len(batches)} batches")
    # TODO: Implement simultaneous calls here
    pass

async def fetch_and_insert_more_posts(db_conn, subreddit_after_list: List[tuple], query: str):
    """Fetch and insert more posts for given subreddits starting from their after keys."""
    print(f"Starting fetch_and_insert_more_posts for {len(subreddit_after_list)} subreddits")
    headers = {"User-Agent": "entityRelationInference/0.1 (by /u/yay_jk)"}

    for subreddit, after in subreddit_after_list:
        print(f"Fetching more posts for {subreddit} starting from after: {after}")
        new_after = await fetch_paginated_posts(subreddit, query, after, headers, db_conn)
        print(f"Finished fetching for {subreddit}, new after: {new_after}")
    print("Completed fetch_and_insert_more_posts")


