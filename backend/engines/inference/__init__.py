"""
Inference module for relationship extraction from posts.

This module provides:
- LLM-based triplet extraction from Reddit posts
- Entity resolution and canonicalization
- Parallel batch processing
"""

from .extraction import run_parallel_extraction, parallel_extraction_stream, persist_triplets_to_db
from .models import (
    Entity,
    Triplet,
    PostAnalysis,
    BatchExtraction,
    EntityGroup,
    EntityResolutionResult,
    ResolvedTriplet,
    ResolvedPostAnalysis,
    RelationshipType,
    ALLOWED_RELATIONS,
)
from .llm_client import (
    get_llm_triplets,
    get_llm_triplets_async,
    resolve_entity_names,
    resolve_entity_names_async,
)
from .text_processing import format_posts_for_llm, minify_text

__all__ = [
    # Main extraction functions
    "run_parallel_extraction",
    "parallel_extraction_stream",
    "persist_triplets_to_db",
    # LLM client functions
    "get_llm_triplets",
    "get_llm_triplets_async",
    "resolve_entity_names",
    "resolve_entity_names_async",
    # Models
    "Entity",
    "Triplet",
    "PostAnalysis",
    "BatchExtraction",
    "EntityGroup",
    "EntityResolutionResult",
    "ResolvedTriplet",
    "ResolvedPostAnalysis",
    "RelationshipType",
    "ALLOWED_RELATIONS",
    # Text processing
    "format_posts_for_llm",
    "minify_text",
]
