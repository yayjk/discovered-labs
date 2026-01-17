"""
Discovery module for subreddit discovery and ranking.

This module provides:
- Subreddit discovery from Reddit search, Google, and Gemini
- Subreddit scoring and ranking based on relevance
- Database operations for discovery data
"""

from .community_finder import (
    score_and_rank_subreddits,
    score_and_rank_subreddits_async,
)
from .core import (
    aggregate_and_filter_subreddits,
    find_subreddits_via_gemini,
    find_subreddits_via_google,
)
from .models import SubredditDiscovery, RedditScrapeSource, SubredditPost
from .subreddit_discovery import scrape_reddit_search
from .subreddit_ranking import (
    get_relevant_posts_from_subreddit,
    scrape_subreddit_search_page,
)
from .legacy import get_relevant_posts_from_subreddit_api
from .helpers import (
    add_jitter,
    get_random_user_agent,
    get_random_impersonate_target,
)
from .constants import (
    USER_AGENTS,
    IMPERSONATE_TARGETS,
    REDDIT_SEARCH_TEMPLATE,
    SUBREDDIT_SEARCH_TEMPLATE,
    GOOGLE_SEARCH_URL,
)
from .db import (
    get_db,
    create_subreddits_table,
    insert_subreddit,
    select_subreddits_by_frequency,
    select_all_subreddits_ordered,
    update_relevance_score,
    delete_subreddits_by_names,
    update_json_response_null,
    close_db,
    init_subreddits_db,
)

__all__ = [
    # Main discovery functions
    "score_and_rank_subreddits",
    "score_and_rank_subreddits_async",
    "aggregate_and_filter_subreddits",
    "find_subreddits_via_gemini",
    "find_subreddits_via_google",
    # Models
    "SubredditDiscovery",
    "RedditScrapeSource",
    "SubredditPost",
    # Scraping functions
    "scrape_reddit_search",
    "get_relevant_posts_from_subreddit",
    "get_relevant_posts_from_subreddit_api",
    "scrape_subreddit_search_page",
    # Helper functions
    "add_jitter",
    "get_random_user_agent",
    "get_random_impersonate_target",
    # Constants
    "USER_AGENTS",
    "IMPERSONATE_TARGETS",
    "REDDIT_SEARCH_TEMPLATE",
    "SUBREDDIT_SEARCH_TEMPLATE",
    "GOOGLE_SEARCH_URL",
    # Database functions
    "get_db",
    "create_subreddits_table",
    "insert_subreddit",
    "select_subreddits_by_frequency",
    "select_all_subreddits_ordered",
    "update_relevance_score",
    "delete_subreddits_by_names",
    "update_json_response_null",
    "close_db",
    "init_subreddits_db",
]
