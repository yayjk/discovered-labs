"""Hacker News discovery module."""

from .core import scrape_hn_non_streaming, scrape_hn_streaming
from .db import (
    init_hn_db,
    create_hn_stories_table,
    create_hn_comments_table,
    insert_hn_story,
    insert_hn_comment,
    close_hn_db,
)

__all__ = [
    "scrape_hn_non_streaming",
    "scrape_hn_streaming",
    "init_hn_db",
    "create_hn_stories_table",
    "create_hn_comments_table",
    "insert_hn_story",
    "insert_hn_comment",
    "close_hn_db",
]
