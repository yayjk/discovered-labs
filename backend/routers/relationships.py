from fastapi import APIRouter, HTTPException
from typing import List
from collections import defaultdict

from database import get_db_connection
from schemas.relationship import Entity, GroupedRelationship, RelationshipDetail, GraphData, GraphNode, GraphLink, GraphData, GraphNode, GraphLink

router = APIRouter(prefix="/relationships", tags=["relationships"])


def build_grouped_relationships(relationships_data: dict) -> List[GroupedRelationship]:
    """Group relationships by type, then by related_entity."""
    grouped = []
    for rel_type, entities_data in relationships_data.items():
        details = []
        for related_entity, data in entities_data.items():
            details.append(RelationshipDetail(
                related_entity=related_entity,
                evidences=[e for e in data["evidences"] if e],
                post_urls=[u for u in data["post_urls"] if u]
            ))
        # Sort details by related_entity for consistent ordering
        details.sort(key=lambda d: d.related_entity)
        grouped.append(GroupedRelationship(
            relationship_type=rel_type,
            details=details
        ))
    # Sort by relationship_type for consistent ordering
    grouped.sort(key=lambda g: g.relationship_type)
    return grouped


@router.get("/graph", response_model=List[Entity])
async def get_relationship_graph():
    """Fetch the full relationship graph with all entities and their relationships."""
    try:
        async with get_db_connection() as db:
            cursor = await db.execute("""
                SELECT subject, relationship, object, evidence, post_url
                FROM triplets
            """)
            rows = await cursor.fetchall()
            
            # Build entity map with left and right relationships grouped by type
            # Structure: {entity_name: {"left": {rel_type: {related_entity: {evidences, post_urls}}}, "right": ...}}
            entities_map: dict[str, dict] = defaultdict(lambda: {
                "left": defaultdict(lambda: defaultdict(lambda: {"evidences": [], "post_urls": []})),
                "right": defaultdict(lambda: defaultdict(lambda: {"evidences": [], "post_urls": []}))
            })
            
            for row in rows:
                subject, relationship, obj, evidence, post_url = row
                
                # Add to subject's right relationships (subject -> relationship -> object)
                entities_map[subject]["right"][relationship][obj]["evidences"].append(evidence)
                entities_map[subject]["right"][relationship][obj]["post_urls"].append(post_url)
                
                # Add to object's left relationships (subject -> relationship -> object)
                entities_map[obj]["left"][relationship][subject]["evidences"].append(evidence)
                entities_map[obj]["left"][relationship][subject]["post_urls"].append(post_url)
            
            # Convert to list of Entity objects
            entities = []
            for name, data in entities_map.items():
                entities.append(Entity(
                    entity_name=name,
                    left_relationships=build_grouped_relationships(data["left"]),
                    right_relationships=build_grouped_relationships(data["right"])
                ))
            
            # Sort by entity name for consistent ordering
            entities.sort(key=lambda e: e.entity_name)
            
            return entities
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/force", response_model=GraphData)
async def get_force_graph():
    """Fetch relationship data in a format compatible with react-force-graph.
    
    Returns nodes (entities) and links (relationships) suitable for force-directed graph visualization.
    Links are aggregated by source-target pair with all evidences and URLs.
    """
    try:
        async with get_db_connection() as db:
            cursor = await db.execute("""
                SELECT subject, relationship, object, evidence, post_url
                FROM triplets
            """)
            rows = await cursor.fetchall()
            
            # Track unique entities and their relationship counts
            entity_counts: dict[str, int] = defaultdict(int)
            
            # Aggregate links by source-target pair
            # Structure: {(source, target): {relationships: set, evidences: list, post_urls: list}}
            link_aggregates: dict[tuple[str, str], dict] = defaultdict(lambda: {
                "relationships": set(),
                "evidences": [],
                "post_urls": []
            })
            
            for row in rows:
                subject, relationship, obj, evidence, post_url = row
                
                # Count relationships for node sizing
                entity_counts[subject] += 1
                entity_counts[obj] += 1
                
                # Aggregate by source-target pair
                pair = (subject, obj)
                link_aggregates[pair]["relationships"].add(relationship)
                if evidence:
                    link_aggregates[pair]["evidences"].append(evidence)
                if post_url:
                    link_aggregates[pair]["post_urls"].append(post_url)
            
            # Calculate curvature for bidirectional links
            bidirectional_pairs = set()
            for (source, target) in link_aggregates.keys():
                if (target, source) in link_aggregates:
                    bidirectional_pairs.add((min(source, target), max(source, target)))
            
            links: List[GraphLink] = []
            for (source, target), data in link_aggregates.items():
                # Add curvature for bidirectional links
                curvature = 0.0
                normalized_pair = (min(source, target), max(source, target))
                if normalized_pair in bidirectional_pairs:
                    curvature = 0.2 if source < target else -0.2
                
                links.append(GraphLink(
                    source=source,
                    target=target,
                    relationships=sorted(list(data["relationships"])),
                    evidences=data["evidences"],
                    post_urls=list(set(data["post_urls"])),  # Dedupe URLs
                    curvature=curvature
                ))
            
            # Create nodes with size based on relationship count
            nodes = [
                GraphNode(
                    id=name,
                    name=name,
                    val=count,  # Node size proportional to connections
                    group=hash(name) % 10  # Simple grouping for coloring
                )
                for name, count in entity_counts.items()
            ]
            
            # Sort for consistent ordering
            nodes.sort(key=lambda n: n.id)
            links.sort(key=lambda l: (l.source, l.target))
            
            return GraphData(nodes=nodes, links=links)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
