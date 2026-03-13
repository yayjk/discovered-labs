from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
import os
import traceback

from engines.hndiscovery import scrape_hn_streaming, init_hn_db, close_hn_db
from engines.inference import parallel_extraction_stream

router = APIRouter(prefix="/analysis", tags=["analysis"])


async def event_stream(query: str, db_path: str = "hn_discovery.db", force_search: bool = False):
    """Generate server-sent events for the analysis process."""
    
    def send_event(event_type: str, data: dict):
        """Format data as SSE event."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    try:
        db_conn = await init_hn_db(db_path)
        delete_db = False

        # Phase 1: Stream events from HN discovery and persistence
        run_inference = True
        async for event_data in scrape_hn_streaming(query=query, db_conn=db_conn, db_path=db_path, force_search=force_search):
            stage = event_data.get("stage")

            if stage == "error":
                yield send_event("error", event_data)
                run_inference = False
            elif stage == "low_confidence":
                yield send_event("low_confidence", event_data)
                run_inference = False
                delete_db = True
            elif stage == "insufficient_results":
                yield send_event("insufficient_results", event_data)
                run_inference = False
                delete_db = True
            else:
                yield send_event("progress", event_data)
            
            # Small delay to ensure events are sent
            await asyncio.sleep(0.05)
        
        if not run_inference:
            # Pipeline terminated early — no inference phase
            return

        # Phase 2: Stream events from entity extraction using the same db_conn
        async for event_data in parallel_extraction_stream(db_conn):
            yield send_event("progress", event_data)

            # Small delay to ensure events are sent
            await asyncio.sleep(0.05)
        
        # Final completion
        yield send_event("complete", {
            "stage": "complete",
            "message": "Full analysis complete!",
            "success": True
        })
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error during analysis: {str(e)}")
        print(f"Traceback:\n{error_traceback}")
        yield send_event("error", {
            "stage": "error",
            "message": f"Error during analysis: {str(e)}",
            "traceback": error_traceback,
            "success": False
        })
    finally:
        if "db_conn" in locals() and db_conn is not None:
            await close_hn_db(db_conn)
        if "delete_db" in locals() and delete_db and os.path.exists(db_path):
            os.remove(db_path)


@router.get("/analyze")
async def analyze_hackernews(query: str = "openai", force_search: bool = False):
    """
    Trigger Hacker News analysis and stream progress updates via Server-Sent Events.
    
    Args:
        query: The search term to look up on Hacker News.
        force_search: When True, skip the LLM confidence check and scrape regardless.
    
    Returns a stream of events with the following stages:
    
    Validation:
    - low_confidence: Query unlikely to yield results (only when force_search=False)
    - insufficient_results: Fewer than 20 items scraped; inference skipped
    
    Phase 1 - Hacker News Discovery:
    - starting: Starting HN scraping
    - page_fetched: Pagination progress for stories/comments
    - stories_complete: Story collection done
    - comments_complete: Comment collection done
    - saving: Saving data to database
    
    Phase 2 - Entity Extraction & Relationship Building:
    - extracting: Extracting entities and inferring relationships
    - batch_completed: Batch processing progress updates
    - building_entities: Building canonical entity list
    - storing: Storing entities and relationships
    
    - complete: Analysis finished successfully
    - error: An error occurred during processing
    """
    db_path = f"{query.lower().replace(' ', '_')}.db"
    return StreamingResponse(
        event_stream(query=query, db_path=db_path, force_search=force_search),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )
