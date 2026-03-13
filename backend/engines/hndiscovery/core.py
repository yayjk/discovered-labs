"""Hacker News discovery utilities for stories and comments scraping."""

from datetime import datetime, timedelta, timezone

import httpx

from .db import init_hn_db, insert_hn_story, insert_hn_comment, close_hn_db
from .confidence import evaluate_query_confidence

HN_SEARCH_BY_DATE_URL = "https://hn.algolia.com/api/v1/search_by_date"


def _last_month_epoch() -> int:
    """Return epoch timestamp for 30 days ago (UTC)."""
    return int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())


def _safe_int(value, default: int = 0) -> int:
    """Safely cast to int."""
    try:
        return int(value)
    except Exception:
        return default


async def _fetch_hits_page(
    client: httpx.AsyncClient,
    query: str,
    tag: str,
    page: int,
    hits_per_page: int,
    created_after_ts: int,
):
    """Fetch one page from HN Algolia API."""
    params = {
        "query": query,
        "tags": tag,
        "page": page,
        "hitsPerPage": hits_per_page,
    }

    if tag == "story":
        params["numericFilters"] = f"points>50,num_comments>10,created_at_i>{created_after_ts}"

    response = await client.get(HN_SEARCH_BY_DATE_URL, params=params)
    response.raise_for_status()
    return response.json()


async def _collect_stories(
    client: httpx.AsyncClient,
    query: str,
    max_items: int,
    hits_per_page: int,
    created_after_ts: int,
    on_page=None,
):
    """Collect stories with API-side numeric filters."""
    stories: list[dict] = []
    page = 0

    while len(stories) < max_items:
        payload = await _fetch_hits_page(
            client=client,
            query=query,
            tag="story",
            page=page,
            hits_per_page=hits_per_page,
            created_after_ts=created_after_ts,
        )

        hits = payload.get("hits", []) or []
        nb_pages = _safe_int(payload.get("nbPages"), 0)

        if not hits:
            break

        for hit in hits:
            object_id = str(hit.get("objectID") or hit.get("story_id") or "")
            if not object_id:
                continue

            stories.append(
                {
                    "object_id": object_id,
                    "story_id": str(hit.get("story_id") or object_id),
                    "created_at_i": _safe_int(hit.get("created_at_i"), 0),
                    "title": (hit.get("title") or "").strip(),
                    "story_text": (hit.get("story_text") or "").strip(),
                    "points": _safe_int(hit.get("points"), 0),
                    "num_comments": _safe_int(hit.get("num_comments"), 0),
                }
            )

            if len(stories) >= max_items:
                break

        if on_page:
            await on_page("story", page, len(hits), len(stories))

        page += 1
        if page >= nb_pages:
            break

    return stories


async def _collect_comments(
    client: httpx.AsyncClient,
    query: str,
    max_items: int,
    hits_per_page: int,
    created_after_ts: int,
    on_page=None,
):
    """Collect comments and filter locally by children length >= 3 and date in last month."""
    comments: list[dict] = []
    page = 0

    while len(comments) < max_items:
        payload = await _fetch_hits_page(
            client=client,
            query=query,
            tag="comment",
            page=page,
            hits_per_page=hits_per_page,
            created_after_ts=created_after_ts,
        )

        hits = payload.get("hits", []) or []
        nb_pages = _safe_int(payload.get("nbPages"), 0)

        if not hits:
            break

        for hit in hits:
            children = hit.get("children")
            if not isinstance(children, list):
                children = []

            children_count = len(children)
            created_at_i = _safe_int(hit.get("created_at_i"), 0)

            if children_count < 3:
                continue
            if created_at_i <= created_after_ts:
                continue

            object_id = str(hit.get("objectID") or "")
            if not object_id:
                continue

            comments.append(
                {
                    "object_id": object_id,
                    "story_id": str(hit.get("story_id") or ""),
                    "created_at_i": created_at_i,
                    "comment_text": (hit.get("comment_text") or "").strip(),
                    "children_count": children_count,
                }
            )

            if len(comments) >= max_items:
                break

        if on_page:
            await on_page("comment", page, len(hits), len(comments))

        page += 1
        if page >= nb_pages:
            break

    return comments


async def scrape_hn_non_streaming(
    query: str,
    db_conn=None,
    db_path: str = "hn_discovery.db",
    max_stories: int = 300,
    max_comments: int = 300,
    hits_per_page: int = 50,
    timeout: int = 20,
):
    """Fetch HN stories and comments, filter, and persist to SQLite stories/comments tables."""
    created_after_ts = _last_month_epoch()
    should_close_db = False
    if db_conn is None:
        db_conn = await init_hn_db(db_path)
        should_close_db = True

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            stories = await _collect_stories(
                client=client,
                query=query,
                max_items=max_stories,
                hits_per_page=hits_per_page,
                created_after_ts=created_after_ts,
            )

            comments = await _collect_comments(
                client=client,
                query=query,
                max_items=max_comments,
                hits_per_page=hits_per_page,
                created_after_ts=created_after_ts,
            )

        for item in stories:
            await insert_hn_story(
                db=db_conn,
                object_id=item["object_id"],
                story_id=item.get("story_id"),
                created_at_i=item.get("created_at_i"),
                title=item.get("title"),
                story_text=item.get("story_text"),
                points=item.get("points"),
                num_comments=item.get("num_comments"),
            )

        for item in comments:
            await insert_hn_comment(
                db=db_conn,
                object_id=item["object_id"],
                story_id=item.get("story_id"),
                comment_text=item.get("comment_text"),
                created_at_i=item.get("created_at_i"),
                children_count=item.get("children_count"),
            )

        await db_conn.commit()

        return {
            "query": query,
            "db_path": db_path,
            "stories_collected": len(stories),
            "comments_collected": len(comments),
            "total_collected": len(stories) + len(comments),
            "created_after_ts": created_after_ts,
        }
    finally:
        if should_close_db:
            await close_hn_db(db_conn)


async def scrape_hn_streaming(
    query: str,
    db_conn=None,
    db_path: str = "hn_discovery.db",
    max_stories: int = 300,
    max_comments: int = 300,
    hits_per_page: int = 50,
    timeout: int = 20,
    force_search: bool = False,
):
    """Streaming variant of HN scraping and persistence with progress events."""
    created_after_ts = _last_month_epoch()
    should_close_db = False
    if db_conn is None:
        db_conn = await init_hn_db(db_path)
        should_close_db = True

    try:
        # ── Confidence check (skipped when force_search=True) ──
        if not force_search:
            confidence = await evaluate_query_confidence(query)
            if confidence.score < 60:
                yield {
                    "stage": "low_confidence",
                    "message": "Query unlikely to generate any results. Would you still like to proceed?",
                    "confidence_score": confidence.score,
                    "confidence_reasoning": confidence.reasoning,
                    "success": False,
                }
                return

        yield {
            "stage": "starting",
            "message": "Starting Hacker News scraping",
            "query": query,
            "created_after_ts": created_after_ts,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:

            async def on_page(item_type: str, page: int, page_hits: int, kept: int):
                yield_event = {
                    "stage": "page_fetched",
                    "message": f"Fetched {item_type} page {page} with {page_hits} hits",
                    "item_type": item_type,
                    "page": page,
                    "page_hits": page_hits,
                    "kept": kept,
                }
                streaming_buffer.append(yield_event)

            streaming_buffer: list[dict] = []

            stories = await _collect_stories(
                client=client,
                query=query,
                max_items=max_stories,
                hits_per_page=hits_per_page,
                created_after_ts=created_after_ts,
                on_page=on_page,
            )

            while streaming_buffer:
                yield streaming_buffer.pop(0)

            yield {
                "stage": "stories_complete",
                "message": f"Collected {len(stories)} stories",
                "count": len(stories),
            }

            comments = await _collect_comments(
                client=client,
                query=query,
                max_items=max_comments,
                hits_per_page=hits_per_page,
                created_after_ts=created_after_ts,
                on_page=on_page,
            )

            while streaming_buffer:
                yield streaming_buffer.pop(0)

            yield {
                "stage": "comments_complete",
                "message": f"Collected {len(comments)} comments",
                "count": len(comments),
            }

        inserted = 0

        for item in stories:
            await insert_hn_story(
                db=db_conn,
                object_id=item["object_id"],
                story_id=item.get("story_id"),
                created_at_i=item.get("created_at_i"),
                title=item.get("title"),
                story_text=item.get("story_text"),
                points=item.get("points"),
                num_comments=item.get("num_comments"),
            )
            inserted += 1

            if inserted % 50 == 0:
                total_rows = len(stories) + len(comments)
                yield {
                    "stage": "saving",
                    "message": f"Saved {inserted}/{total_rows} rows",
                    "saved": inserted,
                    "total": total_rows,
                }

        for item in comments:
            await insert_hn_comment(
                db=db_conn,
                object_id=item["object_id"],
                story_id=item.get("story_id"),
                comment_text=item.get("comment_text"),
                created_at_i=item.get("created_at_i"),
                children_count=item.get("children_count"),
            )
            inserted += 1

            if inserted % 50 == 0:
                total_rows = len(stories) + len(comments)
                yield {
                    "stage": "saving",
                    "message": f"Saved {inserted}/{total_rows} rows",
                    "saved": inserted,
                    "total": total_rows,
                }

        await db_conn.commit()

        total_collected = len(stories) + len(comments)

        # ── Insufficient-results guard ──
        if total_collected < 20:
            yield {
                "stage": "insufficient_results",
                "message": f"Only {total_collected} items found (minimum 20 required). Not enough data to run meaningful analysis.",
                "stories_collected": len(stories),
                "comments_collected": len(comments),
                "total_collected": total_collected,
                "success": False,
            }
            return

        yield {
            "stage": "scraping_complete",
            "message": "Hacker News scraping complete",
            "query": query,
            "db_path": db_path,
            "stories_collected": len(stories),
            "comments_collected": len(comments),
            "total_collected": total_collected,
            "success": True,
        }
    except Exception as exc:
        yield {
            "stage": "error",
            "message": f"Hacker News scraping failed: {exc}",
            "success": False,
        }
    finally:
        if should_close_db:
            await close_hn_db(db_conn)
