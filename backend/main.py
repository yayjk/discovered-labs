import asyncio
import json
from engines.communityFinder import score_and_rank_subreddits
from engines.db import select_json_responses, create_posts_table, insert_post, drop_json_response_column, migrate_to_disk, get_db_connection
from engines.moreData import fetch_and_insert_more_posts
from engines.relationshipInference import run_parallel_extraction
import time
import ast

async def process_json_responses(db, query):
    print("Starting process_json_responses")
    json_responses = await select_json_responses(db)
    print(f"Found {len(json_responses)} json responses")
    await create_posts_table(db)
    print("Created posts table")

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
        
        print(f"Inserted {post_count} initial posts for {subreddit}")

    print(f"Collected {len(subreddit_after_list)} subreddits for more posts")
    await drop_json_response_column(db)
    print("Dropped json_response column")
    disk_db = await migrate_to_disk(db)
    print("Migrated to disk database")
    # await fetch_and_insert_more_posts(disk_db, subreddit_after_list, query)
    # print("Fetched and inserted more posts")
    await disk_db.close()


def main():
    query = "tesla"
    db = score_and_rank_subreddits(query=query, min_frequency=3)
    asyncio.run(process_json_responses(db, query))
    time.sleep(2)  # Small delay to ensure DB is closed before extraction
    asyncio.run(run_parallel_extraction())

if __name__ == "__main__":
    main()


