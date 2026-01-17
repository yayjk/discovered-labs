"""Data models for the discovery module."""

from enum import Enum
from typing import List
from pydantic import BaseModel


class RedditScrapeSource(str, Enum):
    """Source for Reddit scraping."""
    HTML = "html"
    API = "api"


class SubredditDiscovery(BaseModel):
    """Model for subreddit discovery results."""
    subreddits: List[str] = []


class SubredditPost(BaseModel):
    """Normalized model for a subreddit post."""
    post_id: str = ""
    post_url: str = ""
    post_title: str = ""
    self_text: str = ""
    ups: int = 0
    num_comments: int = 0
    created_datetime: str = ""
