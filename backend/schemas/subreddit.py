from pydantic import BaseModel
from typing import Optional


class Subreddit(BaseModel):
    subreddit_name: str
    engagement_score: Optional[float] = None
    freshness_score: Optional[float] = None
    frequency_score: Optional[float] = None
    relevance_score: Optional[float] = None
