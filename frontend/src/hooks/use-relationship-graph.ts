import { useQuery } from "@tanstack/react-query";

const API_BASE_URL = "http://localhost:8000";

export interface RelationshipDetail {
  related_entity: string;
  evidences: string[];
  post_urls: string[];
}

export interface GroupedRelationship {
  relationship_type: string;
  details: RelationshipDetail[];
}

export interface Entity {
  entity_name: string;
  left_relationships: GroupedRelationship[];
  right_relationships: GroupedRelationship[];
}

async function fetchRelationshipGraph(): Promise<Entity[]> {
  const response = await fetch(`${API_BASE_URL}/relationships/graph`);
  if (!response.ok) {
    throw new Error("Failed to fetch relationship graph");
  }
  return response.json();
}

export function useRelationshipGraph() {
  return useQuery({
    queryKey: ["relationship-graph"],
    queryFn: fetchRelationshipGraph,
  });
}

// Helper to count total relationships
export function countRelationships(relationships: GroupedRelationship[]): number {
  return relationships.reduce((sum, group) => sum + group.details.length, 0);
}
