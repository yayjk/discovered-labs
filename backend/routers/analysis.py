from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
import traceback

from engines.discovery.community_finder import test_score_and_rank_subreddits_streaming
from engines.inference import parallel_extraction_stream
from database import get_db_connection

router = APIRouter(prefix="/analysis", tags=["analysis"])


async def event_stream():
    """Generate server-sent events for the analysis process."""
    
    def send_event(event_type: str, data: dict):
        """Format data as SSE event."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    try:
        db_conn = None
        
        # Phase 1: Stream events from subreddit discovery and ranking
        async for event_data in test_score_and_rank_subreddits_streaming():
            stage = event_data.get("stage")
            
            # Capture db_conn from internal event
            if stage == "_internal_db_conn":
                db_conn = event_data.get("db_conn")
                continue
            
            # Send progress event for all stages
            if stage == "error":
                yield send_event("error", event_data)
            else:
                yield send_event("progress", event_data)
            
            # Small delay to ensure events are sent
            await asyncio.sleep(0.05)
        
        # Phase 2: Stream events from entity extraction using the same db_conn
        if db_conn:
            async for event_data in parallel_extraction_stream(db_conn):
                stage = event_data.get("stage")
                
                # All extraction events are progress events
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


@router.get("/analyze")
async def analyze_subreddits():
    """
    Trigger subreddit analysis and stream progress updates via Server-Sent Events.
    
    Returns a stream of events with the following stages:
    
    Phase 1 - Subreddit Discovery & Ranking:
    - crawling_reddit: Crawling Reddit search results
    - searching_google: Searching Google for subreddits
    - asking_gemini: Asking Gemini for recommendations
    - aggregating: Aggregating results from all sources
    - aggregated: Results aggregated with count and list
    - ranking: Ranking subreddits based on relevance
    - processing_batch: Processing each batch of subreddits
    - saving: Processing and saving data to database
    
    Phase 2 - Entity Extraction & Relationship Building:
    - extracting: Extracting entities and inferring relationships
    - batch_completed: Batch processing progress updates
    - building_entities: Building canonical entity list
    - storing: Storing entities and relationships
    
    - complete: Analysis finished successfully
    - error: An error occurred during processing
    """
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )
