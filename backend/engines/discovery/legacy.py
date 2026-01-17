"""Legacy methods for subreddit discovery (deprecated)."""

from curl_cffi import requests as curl_requests
from curl_cffi.requests import AsyncSession
from datetime import datetime

from typing import List

from .models import SubredditPost


def find_subreddits_via_reddit_posts_search(query: str, min_comments: int = 10) -> List[str]:
    """Fetch posts from `search query` and return a list of subreddit names.

    Rules:
    - Skip posts where `num_comments` is less than `min_comments`.
    - If a subreddit is already added, skip subsequent posts from the same subreddit.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    url="https://www.reddit.com/search.json?q={query}&sort=relevance&t=month&limit=25"

    try:
        resp = curl_requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch posts from Reddit: {exc}") from exc

    return parse_subreddits_from_search_json(payload, min_comments=min_comments)


def parse_subreddits_from_search_json(payload: dict, min_comments: int = 10) -> List[str]:
    """
    Parse Reddit search API JSON payload into a list of subreddit names.

    Args:
        payload: Reddit API JSON response
        min_comments: Minimum comments to include a subreddit

    Returns:
        List of subreddit names
    """
    results: List[str] = []

    for child in payload.get("data", {}).get("children", []):
        if not isinstance(child, dict):
            continue
        data = child.get("data", {})

        # Get subreddit identifier
        subreddit_prefixed = data.get("subreddit_name_prefixed")

        # Skip low-engagement posts
        try:
            num_comments = int(data.get("num_comments", 0))
        except (TypeError, ValueError):
            continue
        if num_comments < min_comments:
            continue

        if subreddit_prefixed and subreddit_prefixed not in results:
            results.append(subreddit_prefixed)

    return results


def test_find_subreddits_via_reddit_posts_search_json(file_path: str, min_comments: int = 10) -> List[str]:
    """
    Test helper to parse Reddit search API JSON payload from a local file.

    Args:
        file_path: Path to a local JSON file containing Reddit API response
        min_comments: Minimum comments to include a subreddit

    Returns:
        List of subreddit names
    """
    try:
        import json

        with open(file_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return parse_subreddits_from_search_json(payload, min_comments=min_comments)
    except Exception as exc:
        print(f"Failed to parse local JSON: {exc}")
        return []


async def get_relevant_posts_from_subreddit_api(
    subreddit: str,
    query: str,
    timeout: int = 10,
) -> List[SubredditPost]:
    """
    Fetch subreddit search results from the Reddit API and return normalized posts.

    Args:
        subreddit: Subreddit name (with or without r/)
        query: Search query
        timeout: Request timeout in seconds

    Returns:
        List of normalized posts
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
    }

    search_url = f"https://www.reddit.com/{subreddit}/search.json"
    params = {"q": query, "sort": "new", "restrict_sr": "1", "limit": 100, "include_over_18": "on"}

    try:
        async with AsyncSession() as client:
            resp_search = await client.get(search_url, headers=headers, params=params, timeout=timeout)
            if resp_search.status_code != 200:
                print(f"Failed to fetch posts for {subreddit}, status code: {resp_search.status_code}")
                return []

            payload = resp_search.json()
    except Exception as exc:
        print(f"Failed to fetch posts from Reddit API: {exc}")
        return []

    return parse_subreddit_posts_from_api_json(payload)


def parse_subreddit_posts_from_api_json(payload: dict) -> List[SubredditPost]:
    """
    Parse Reddit API JSON payload into normalized posts.

    Args:
        payload: Reddit API JSON response

    Returns:
        List of normalized posts
    """
    results: List[SubredditPost] = []
    for child in payload.get("data", {}).get("children", []):
        data = child.get("data", {}) if isinstance(child, dict) else {}
        created_utc = data.get("created_utc")
        created_datetime = ""
        try:
            if created_utc is not None:
                created_datetime = datetime.utcfromtimestamp(float(created_utc)).isoformat() + "Z"
        except Exception:
            created_datetime = ""

        permalink = data.get("permalink") or ""
        post_url = f"https://old.reddit.com{permalink}" if permalink else ""

        results.append(
            SubredditPost(
                post_id=data.get("id") or "",
                post_url=post_url,
                post_title=data.get("title") or "",
                self_text=data.get("selftext") or "",
                ups=int(data.get("ups") or 0),
                num_comments=int(data.get("num_comments") or 0),
                created_datetime=created_datetime,
            )
        )

    return results


def test_get_relevant_posts_from_subreddit_api_json(file_path: str) -> List[SubredditPost]:
    """
    Test helper to parse Reddit API JSON payload from a local file.

    Args:
        file_path: Path to a local JSON file containing Reddit API response

    Returns:
        List of parsed posts
    """
    try:
        import json

        with open(file_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return parse_subreddit_posts_from_api_json(payload)
    except Exception as exc:
        print(f"Failed to parse local JSON: {exc}")
        return []

        