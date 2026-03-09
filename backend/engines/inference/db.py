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
    """Retrieves HN stories and comments and returns them in extraction input format."""
    db.row_factory = aiosqlite.Row

    stories_query = """
        SELECT object_id, story_id, title, story_text
        FROM hn_stories
    """
    comments_query = """
        SELECT object_id, story_id, comment_text
        FROM hn_comments
    """

    async with db.execute(stories_query) as cursor:
        story_rows = await cursor.fetchall()

    async with db.execute(comments_query) as cursor:
        comment_rows = await cursor.fetchall()

    stories = [
        {
            "id": f"story_{row['object_id']}",
            "source": "hackernews",
            "text": f"{row['title'] or ''}\n{row['story_text'] or ''}".strip(),
            "url": f"https://news.ycombinator.com/item?id={row['story_id'] or row['object_id']}",
        }
        for row in story_rows
    ]

    comments = [
        {
            "id": f"comment_{row['object_id']}",
            "source": "hackernews",
            "text": row["comment_text"] or "",
            "url": f"https://news.ycombinator.com/item?id={row['object_id']}",
        }
        for row in comment_rows
    ]

    return stories + comments
