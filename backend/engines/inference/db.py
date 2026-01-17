"""Database operations for the inference module."""

import aiosqlite
from typing import List


def get_db_connection(db_path: str):
    """Returns an active connection to the database."""
    return aiosqlite.connect(db_path)


async def create_triplets_table(db):
    """Create the triplets table."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS triplets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            relationship TEXT NOT NULL,
            object TEXT NOT NULL,
            evidence TEXT,
            post_id TEXT,
            post_url TEXT,
            justification TEXT
        )
    """)
    await db.commit()


async def insert_triplet(db, subject: str, relationship: str, object: str, evidence: str, post_id: str, post_url: str, justification: str):
    """Insert a triplet into the database."""
    await db.execute("""
        INSERT INTO triplets (subject, relationship, object, evidence, post_id, post_url, justification)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (subject, relationship, object, evidence, post_id, post_url, justification))
    await db.commit()


async def insert_triplets_batch(db, triplets: List[tuple]):
    """Insert multiple triplets in a single transaction."""
    await db.executemany("""
        INSERT INTO triplets (subject, relationship, object, evidence, post_id, post_url, justification)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, triplets)
    await db.commit()


async def fetch_all_posts(db) -> List[dict]:
    """Retrieves all posts from the DB and returns them as a list of dicts."""
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT pid as id, subreddit_name, title, selftext, url FROM posts") as cursor:
        rows = await cursor.fetchall()
        return [
            {"id": row["id"], "subreddit": row["subreddit_name"], "text": f"{row['title']}\n{row['selftext']}", "url": row["url"]} 
            for row in rows
        ]
