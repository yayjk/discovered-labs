from fastapi import APIRouter, HTTPException
from typing import List

from database import get_db_connection
from schemas.subreddit import Subreddit

router = APIRouter(prefix="/subreddits", tags=["subreddits"])


@router.get("", response_model=List[Subreddit])
async def get_subreddits(report: str = "tesla"):
    """Fetch all subreddits from the database."""
    try:
        db_path = "reports/tesla.db" if report == "tesla" else "subreddits.db"
        async with get_db_connection(db_path) as db:
            cursor = await db.execute("""
                SELECT subreddit_name, engagement_score, freshness_score, frequency_score, relevance_score 
                FROM subreddits 
                ORDER BY relevance_score DESC
            """)
            rows = await cursor.fetchall()
            
            return [
                Subreddit(
                    subreddit_name=row[0],
                    engagement_score=row[1],
                    freshness_score=row[2],
                    frequency_score=row[3],
                    relevance_score=row[4]
                )
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{subreddit_name}", response_model=Subreddit)
async def get_subreddit(subreddit_name: str, report: str = "tesla"):
    """Fetch a specific subreddit by name."""
    try:
        db_path = "reports/tesla.db" if report == "tesla" else "subreddits.db"
        async with get_db_connection(db_path) as db:
            cursor = await db.execute("""
                SELECT subreddit_name, engagement_score, freshness_score, frequency_score, relevance_score 
                FROM subreddits 
                WHERE subreddit_name = ?
            """, (subreddit_name,))
            row = await cursor.fetchone()
            
            if row is None:
                raise HTTPException(status_code=404, detail=f"Subreddit '{subreddit_name}' not found")
            
            return Subreddit(
                subreddit_name=row[0],
                engagement_score=row[1],
                freshness_score=row[2],
                frequency_score=row[3],
                relevance_score=row[4]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
