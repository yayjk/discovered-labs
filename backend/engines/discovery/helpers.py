"""Helper utilities for the discovery module."""

import random
import asyncio

from .constants import USER_AGENTS, IMPERSONATE_TARGETS


async def add_jitter(min_delay: float = 0.5, max_delay: float = 2.5):
    """
    Add random jitter (delay) between requests to avoid detection.
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
    """
    jitter = random.uniform(min_delay, max_delay)
    await asyncio.sleep(jitter)


def get_random_user_agent() -> str:
    """
    Get a random user agent string from the available options.
    
    Returns:
        A random user agent string
    """
    return random.choice(list(USER_AGENTS.values()))


def get_random_impersonate_target() -> str:
    """
    Get a random impersonate target for curl_cffi browser mimicking.
    
    Returns:
        A random impersonate target string
    """
    return random.choice(IMPERSONATE_TARGETS)


async def process_json_responses(db, query):
    """Process JSON responses from database and populate posts table.
    
    Args:
        db: Database connection with subreddits table
        query: The search query used for discovery
    """
    import ast
    from pathlib import Path
    
    # Import from local db module
    from .db import (
        select_json_responses,
        create_posts_table,
        insert_post,
        drop_json_response_column,
        migrate_to_disk
    )
    
    json_responses = await select_json_responses(db)
    await create_posts_table(db)

    subreddit_after_list = []
    for subreddit, json_resp in json_responses:
        if not json_resp:
            continue
            
        try:
            # Parse the string representation of posts list
            posts = ast.literal_eval(json_resp)
        except Exception as e:
            print(f"Error parsing json_resp for {subreddit}: {e}")
            continue
        
        post_count = 0
        for post in posts:
            try:
                # Extract fields from the new post format
                title = post.get('post_title', '')
                selftext = post.get('self_text', '')
                ups = int(post.get('ups', 0) or 0)
                num_comments = int(post.get('num_comments', 0) or 0)
                
                # Convert created_datetime (ISO format) to Unix timestamp
                created_utc = 0
                created_datetime = post.get('created_datetime', '')
                if created_datetime:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(created_datetime.replace('Z', '+00:00'))
                        created_utc = int(dt.timestamp())
                    except Exception:
                        pass
                
                url = post.get('post_url', '')
                post_id = post.get('post_id', '').replace('t3_', '')  # Remove t3_ prefix if present
                
                await insert_post(db, subreddit, title, selftext, ups, num_comments, created_utc, url, post_id)
                post_count += 1
            except Exception as e:
                print(f"Error inserting post for {subreddit}: {e}")
                continue

    await drop_json_response_column(db)
    disk_db = await migrate_to_disk(db)
    
    return disk_db
