from .subreddits import router as subreddits_router
from .relationships import router as relationships_router
from .analysis import router as analysis_router

__all__ = ["subreddits_router", "relationships_router", "analysis_router"]
