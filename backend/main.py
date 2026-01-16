import asyncio
import json
from engines.communityFinder import score_and_rank_subreddits
from engines.db import select_json_responses, create_posts_table, insert_post, drop_json_response_column, migrate_to_disk, get_db_connection
from engines.moreData import fetch_and_insert_more_posts
from engines.relationshipInference import run_parallel_extraction
import time


async def process_json_responses(db, query):
    print("Starting process_json_responses")
    json_responses = await select_json_responses(db)
    print(f"Found {len(json_responses)} json responses")
    await create_posts_table(db)
    print("Created posts table")

    subreddit_after_list = []
    for subreddit, json_resp in json_responses:
        response = json.loads(json_resp)
        post_count = 0
        for child in response['data']['children']:
            post = child['data']
            await insert_post(db, subreddit, post['title'], post.get('selftext', ''), post['ups'], post['downs'], post['num_comments'], post['created_utc'], post['url'], post['id'])
            post_count += 1
        print(f"Inserted {post_count} initial posts for {subreddit}")
        after = response['data'].get('after')
        if after:
            subreddit_after_list.append((subreddit, after))
            print(f"Added {subreddit} with after: {after}")

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
    sleep(2)  # Small delay to ensure DB is closed before extraction
    time.sleep(2)  # Small delay to ensure DB is closed before extraction
    asyncio.run(run_parallel_extraction())

if __name__ == "__main__":
    main()


