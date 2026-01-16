from pydantic import BaseModel
from typing import List, Optional


class GraphNode(BaseModel):
    """Node in the relationship graph (compatible with react-force-graph)."""
    id: str
    name: str
    val: int = 1  # Node size/weight - can be based on relationship count
    group: Optional[int] = None  # For grouping/coloring nodes


class GraphLink(BaseModel):
    """Link/edge in the relationship graph (compatible with react-force-graph)."""
    source: str
    target: str
    relationships: List[str]  # All relationship types between source and target
    evidences: List[str]  # All evidences for this edge
    post_urls: List[str]  # All post URLs for this edge
    curvature: float = 0.0  # For curved links when multiple edges between same nodes


class GraphData(BaseModel):
    """Full graph data structure (compatible with react-force-graph)."""
    nodes: List[GraphNode]
    links: List[GraphLink]


class RelationshipDetail(BaseModel):
    related_entity: str
    evidences: List[str]
    post_urls: List[str]


class GroupedRelationship(BaseModel):
    relationship_type: str
    details: List[RelationshipDetail]


class Entity(BaseModel):
    entity_name: str
    left_relationships: List[GroupedRelationship]  # Entity is the object (subject -> relationship -> entity)
    right_relationships: List[GroupedRelationship]  # Entity is the subject (entity -> relationship -> object)
