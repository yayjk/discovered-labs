import aiosqlite

async def get_db():
    """Create and return an in-memory SQLite database connection."""
    return await aiosqlite.connect(":memory:")

async def create_subreddits_table(db):
    """Create the subreddits table."""
    await db.execute("""
        CREATE TABLE subreddits (
            subreddit_name TEXT PRIMARY KEY,
            json_response TEXT,
            engagement_score REAL,
            freshness_score REAL,
            frequency_score REAL,
            relevance_score REAL
        )
    """)
    await db.commit()

async def insert_subreddit(db, subreddit_name, json_response, engagement_score, freshness_score, frequency_score):
    """Insert a subreddit into the database."""
    await db.execute("""
        INSERT INTO subreddits (subreddit_name, json_response, engagement_score, freshness_score, frequency_score)
        VALUES (?, ?, ?, ?, ?)
    """, (subreddit_name, json_response, engagement_score, freshness_score, frequency_score))
    await db.commit()

async def select_subreddits_by_frequency(db, min_frequency):
    """Select subreddits where frequency_score >= min_frequency."""
    cursor = await db.execute("SELECT subreddit_name, engagement_score, freshness_score, frequency_score FROM subreddits WHERE frequency_score >= ?", (min_frequency,))
    return await cursor.fetchall()

async def select_all_subreddits_ordered(db):
    """Select all subreddits ordered by relevance_score descending."""
    cursor = await db.execute("SELECT subreddit_name, json_response, engagement_score, freshness_score, frequency_score, relevance_score FROM subreddits ORDER BY relevance_score DESC")
    return await cursor.fetchall()

async def update_relevance_score(db, subreddit_name, relevance_score):
    """Update the relevance_score for a subreddit."""
    await db.execute("UPDATE subreddits SET relevance_score = ? WHERE subreddit_name = ?", (relevance_score, subreddit_name))
    await db.commit()

async def delete_subreddits_by_names(db, subreddit_names):
    """Delete subreddits by their names."""
    if not subreddit_names:
        return
    placeholders = ','.join('?' * len(subreddit_names))
    await db.execute(f"DELETE FROM subreddits WHERE subreddit_name IN ({placeholders})", subreddit_names)
    await db.commit()

async def update_json_response_null(db, subreddit_name):
    """Set json_response to NULL for a subreddit."""
    await db.execute("UPDATE subreddits SET json_response = NULL WHERE subreddit_name = ?", (subreddit_name,))
    await db.commit()

async def close_db(db):
    """Close the database connection."""
    await db.close()

async def migrate_to_disk(db, db_path="subreddits.db"):
    """Migrate the in-memory database to a file-based database."""
    disk_db = await aiosqlite.connect(db_path)
    await db.backup(disk_db)
    await db.close()
    return disk_db

async def create_posts_table(db):
    """Create the posts table."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            subreddit_name TEXT,
            title TEXT,
            selftext TEXT,
            ups INTEGER,
            num_comments INTEGER,
            created_utc REAL,
            url TEXT,
            pid TEXT
        )
    """)
    await db.commit()

async def select_posts_paginated(db, min_upvotes=5, min_comments=5, limit=100, offset=0):
    """Select posts with minimum upvotes or comments, with pagination."""
    cursor = await db.execute("""
        SELECT subreddit_name, json_response
        FROM posts
        LIMIT ? OFFSET ?
    """, (limit, offset))
    return await cursor.fetchall()

async def select_json_responses(db):
    """Select all json_responses with subreddit_name."""
    cursor = await db.execute("SELECT subreddit_name, json_response FROM subreddits WHERE json_response IS NOT NULL")
    return await cursor.fetchall()

async def drop_json_response_column(db):
    """Drop the json_response column from subreddits table."""
    await db.execute("ALTER TABLE subreddits DROP COLUMN json_response")
    await db.commit()

async def insert_post(db, subreddit_name, title, selftext, ups, num_comments, created_utc, url, pid):
    """Insert a post entry into the posts table."""
    await db.execute("INSERT INTO posts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (subreddit_name, title, selftext, ups, num_comments, created_utc, url, pid))
    await db.commit()