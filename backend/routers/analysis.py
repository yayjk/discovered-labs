from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
import traceback

from engines.hndiscovery import scrape_hn_streaming, init_hn_db, close_hn_db
from engines.inference import parallel_extraction_stream

router = APIRouter(prefix="/analysis", tags=["analysis"])


async def event_stream(query: str, db_path: str = "hn_discovery.db"):
    """Generate server-sent events for the analysis process."""
    
    def send_event(event_type: str, data: dict):
        """Format data as SSE event."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    try:
        db_conn = await init_hn_db(db_path)

        # Phase 1: Stream events from HN discovery and persistence
        async for event_data in scrape_hn_streaming(query=query, db_conn=db_conn, db_path=db_path):
            stage = event_data.get("stage")

            # Send progress event for all stages
            if stage == "error":
                yield send_event("error", event_data)
            else:
                yield send_event("progress", event_data)
            
            # Small delay to ensure events are sent
            await asyncio.sleep(0.05)
        
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


@router.get("/analyze")
async def analyze_hackernews(query: str = "openai"):
    """
    Trigger Hacker News analysis and stream progress updates via Server-Sent Events.
    
    Returns a stream of events with the following stages:
    
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
        event_stream(query=query, db_path=db_path),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )
