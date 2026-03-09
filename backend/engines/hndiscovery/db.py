"""Database operations for Hacker News discovery."""

import aiosqlite


async def init_hn_db(db_path: str = "hn_discovery.db"):
    """Initialize SQLite DB and ensure stories/comments tables exist."""
    db_conn = await aiosqlite.connect(db_path)
    await create_hn_stories_table(db_conn)
    await create_hn_comments_table(db_conn)
    return db_conn


async def create_hn_stories_table(db):
    """Create table for HN stories."""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS hn_stories (
            object_id TEXT PRIMARY KEY,
            story_id TEXT,
            created_at_i INTEGER,
            title TEXT,
            story_text TEXT,
            points INTEGER,
            num_comments INTEGER
        )
        """
    )
    await db.commit()


async def create_hn_comments_table(db):
    """Create table for HN comments."""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS hn_comments (
            object_id TEXT PRIMARY KEY,
            story_id TEXT,
            comment_text TEXT,
            created_at_i INTEGER,
            children_count INTEGER
        )
        """
    )
    await db.commit()


async def insert_hn_story(
    db,
    object_id: str,
    story_id: str | None,
    created_at_i: int | None,
    title: str | None,
    story_text: str | None,
    points: int | None,
    num_comments: int | None,
):
    """Insert or replace a single HN story."""
    await db.execute(
        """
        INSERT OR REPLACE INTO hn_stories (
            object_id,
            story_id,
            created_at_i,
            title,
            story_text,
            points,
            num_comments
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            object_id,
            story_id,
            created_at_i,
            title,
            story_text,
            points,
            num_comments,
        ),
    )


async def insert_hn_comment(
    db,
    object_id: str,
    story_id: str | None,
    comment_text: str | None,
    created_at_i: int | None,
    children_count: int | None,
):
    """Insert or replace a single HN comment."""
    await db.execute(
        """
        INSERT OR REPLACE INTO hn_comments (
            object_id,
            story_id,
            comment_text,
            created_at_i,
            children_count
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (object_id, story_id, comment_text, created_at_i, children_count),
    )


async def close_hn_db(db):
    """Close DB connection."""
    await db.close()
